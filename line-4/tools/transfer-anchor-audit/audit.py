#!/usr/bin/env python3
"""Recheck the known block hashes of a bounded ERC-20 capture, without a wallet."""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "groups_for_anchor_audit", HERE.parent / "transfer-transaction-groups" / "groups.py")
groups = importlib.util.module_from_spec(spec)
spec.loader.exec_module(groups)
window, reader = groups.window, groups.reader
MAX_BLOCKS = 64
LIMITATIONS = (
    "Hashes are compared with a provider's numbered-block responses, not verified "
    "against consensus. Matching hashes do not prove event inclusion, log "
    "completeness, balances, prices, pool activity or finality. Only boundaries "
    "and blocks with observed transfers are checked; other interior blocks are "
    "not checked. Reads are sequential, not an atomic snapshot. A changed hash "
    "is an observation conflict, not by itself proof of a reorganization. "
    "Replay checks retained evidence, not the current chain."
)


def plan(capture):
    """Validate all saved evidence before making even the first network request."""
    checked = groups.report(capture)
    known = {}
    for key, role in (("from_block_anchor", "start"), ("to_block_anchor", "end")):
        anchor = checked[key]
        item = known.setdefault(anchor["number"], {
            "number": anchor["number"], "saved_hash": anchor["hash"],
            "roles": [], "transfer_count": 0,
        })
        item["roles"].append(role)
    for transaction in checked["transactions"]:
        for event in transaction["transfers"]:
            item = known.setdefault(event["block"], {
                "number": event["block"], "saved_hash": event["block_hash"],
                "roles": [], "transfer_count": 0,
            })
            if item["saved_hash"] != event["block_hash"]:
                raise window.RpcError("conflicting saved block hashes")
            if "transfers" not in item["roles"]:
                item["roles"].append("transfers")
            item["transfer_count"] += 1
    if len(known) > MAX_BLOCKS:
        raise window.RpcError("audit exceeds 64 distinct known blocks; use a smaller capture")
    return checked, [known[number] for number in sorted(known)]


def observed_block(block, number):
    """Null means unavailable, never a matching or empty block observation."""
    if block is None:
        return None
    if type(block) is not dict:
        raise window.RpcError("observed block must be an object or null")
    if window.quantity(block.get("number"), "observed block number") != number:
        raise window.RpcError("observed block has the wrong number")
    return {"number": hex(number),
            "hash": window.hex_bytes(block.get("hash"), 32, "observed block hash")}


def collect(capture, endpoint=window.DEFAULT_RPC):
    """At most 65 allowlisted public reads; no retries or partial success output."""
    _, expected = plan(capture)
    window.validate_endpoint(endpoint)
    chain = window.quantity(window.rpc(endpoint, "eth_chainId", []), "chain ID")
    if chain != 1:
        raise window.RpcError("Ethereum mainnet required")
    observations = []
    for item in expected:
        number = item["number"]
        block = window.rpc(endpoint, "eth_getBlockByNumber", [hex(number), False])
        observations.append({"requested_number": number,
                             "block": observed_block(block, number)})
    return {
        "kind": "erc20-transfer-anchor-observations", "schema_version": 1,
        "chain_id": 1, "rpc": endpoint,
        "observed_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "observations": observations,
    }


def report(capture, evidence):
    """Recompute verdicts; never trust stored verdicts or a partial observation set."""
    checked, expected = plan(capture)
    if (type(evidence) is not dict
            or evidence.get("kind") != "erc20-transfer-anchor-observations"
            or type(evidence.get("schema_version")) is not int
            or evidence["schema_version"] != 1
            or type(evidence.get("chain_id")) is not int or evidence["chain_id"] != 1):
        raise window.RpcError("mainnet anchor evidence schema 1 required")
    if type(evidence.get("rpc")) is not str:
        raise window.RpcError("evidence RPC URL must be a string")
    window.validate_endpoint(evidence["rpc"])
    timestamp = evidence.get("observed_at")
    if type(timestamp) is not str or len(timestamp) > 40:
        raise window.RpcError("timezone-aware observation timestamp required")
    try:
        parsed = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("missing timezone")
    except ValueError as exc:
        raise window.RpcError("invalid observation timestamp") from exc
    observations = evidence.get("observations")
    if type(observations) is not list or len(observations) != len(expected):
        raise window.RpcError("evidence must cover every planned block exactly once")
    rows = []
    for saved, item in zip(expected, observations):
        if (type(item) is not dict or set(item) != {"requested_number", "block"}
                or type(item["requested_number"]) is not int
                or item["requested_number"] != saved["number"]):
            raise window.RpcError("observations must match planned numbers in ascending order")
        current = observed_block(item["block"], saved["number"])
        status = ("unavailable" if current is None else
                  "matching" if current["hash"] == saved["saved_hash"] else "changed")
        rows.append(dict(saved, observed_hash=None if current is None else current["hash"],
                         status=status))
    counts = {name: sum(row["status"] == name for row in rows)
              for name in ("matching", "changed", "unavailable")}
    status = "changed" if counts["changed"] else "unavailable" if counts["unavailable"] else "matching"
    return {
        "kind": "erc20-transfer-anchor-audit", "schema_version": 1,
        "read_only": True, "raw_logs_revalidated": True,
        "status": status, "token": checked["token"], "chain_id": 1,
        "token_address": checked["token_address"],
        "from_block": checked["from_block"], "to_block": checked["to_block"],
        "transfer_count": checked["transfer_count"], "checked_block_count": len(rows),
        "unchecked_interior_block_count": checked["to_block"] - checked["from_block"] + 1 - len(rows),
        "counts": counts, "blocks": rows, "rpc": evidence["rpc"],
        "observed_at": timestamp, "max_checked_blocks": MAX_BLOCKS,
        "limitations": LIMITATIONS,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true", help="replay retained real ZTO evidence offline")
    source.add_argument("--capture", type=Path, help="saved workspace transfer capture")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="recheck public numbered-block hashes now")
    mode.add_argument("--evidence", type=Path, help="replay saved anchor observations offline")
    parser.add_argument("--rpc", help="public mainnet RPC, default PublicNode; live only")
    args = parser.parse_args(argv)
    if args.demo:
        if args.live or args.evidence or args.rpc:
            parser.error("--demo uses its retained capture and observations only")
        capture = reader.read_capture(HERE.parent / "transfer-crosscheck" / "publicnode.json")
        evidence = reader.read_capture(HERE / "observations.json")
    else:
        if not (args.live or args.evidence):
            parser.error("choose --live or --evidence explicitly")
        if args.rpc and not args.live:
            parser.error("--rpc requires --live")
        capture = reader.read_capture(args.capture)
        evidence = collect(capture, args.rpc or window.DEFAULT_RPC) if args.live else reader.read_capture(args.evidence)
    result = report(capture, evidence)
    result["mode"] = "live" if args.live else "replay"
    result["evidence"] = evidence
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "matching" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, window.RpcError) as exc:
        print("transfer-anchor-audit: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
