// Preserve ancestor pixels; only composite the installed image tool's new mark.
const fs = require('fs');
const zlib = require('zlib');
const crypto = require('crypto');
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
function crc32(b) { let c=0xffffffff; for (const v of b) { c ^= v; for(let k=0;k<8;k++) c=(c>>>1)^((c&1)?0xedb88320:0); } return (c^0xffffffff)>>>0; }
function decode(b) {
 if (!b.subarray(0,8).equals(Buffer.from('89504e470d0a1a0a','hex'))) throw Error('PNG required');
 let w,h,channels; const chunks=[];
 for(let p=8;p<b.length;) {
  const n=b.readUInt32BE(p), type=b.toString('ascii',p+4,p+8), data=b.subarray(p+8,p+8+n);
  if(crc32(b.subarray(p+4,p+8+n))!==b.readUInt32BE(p+8+n)) throw Error('CRC');
  if(type==='IHDR') { w=data.readUInt32BE(0);h=data.readUInt32BE(4);channels=data[9]===2?3:data[9]===6?4:0; if(data[8]!==8||!channels||data[12]) throw Error('unsupported PNG'); }
  if(type==='IDAT') chunks.push(data);
  p+=n+12; if(type==='IEND') break;
 }
 const raw=zlib.inflateSync(Buffer.concat(chunks)); const stride=w*channels, out=Buffer.alloc(w*h*3); let prev=Buffer.alloc(stride); const alpha=Buffer.alloc(w*h,255);
 if(raw.length!==(stride+1)*h) throw Error('PNG extent');
 for(let y=0;y<h;y++) {
  const f=raw[y*(stride+1)], row=Buffer.from(raw.subarray(y*(stride+1)+1,(y+1)*(stride+1)));
  for(let x=0;x<stride;x++) {
   const a=x>=channels?row[x-channels]:0,b=prev[x],c=x>=channels?prev[x-channels]:0;
   let v=0; if(f===1)v=a;else if(f===2)v=b;else if(f===3)v=Math.floor((a+b)/2);else if(f===4){const p=a+b-c,da=Math.abs(p-a),db=Math.abs(p-b),dc=Math.abs(p-c);v=da<=db&&da<=dc?a:db<=dc?b:c;}else if(f!==0)throw Error('filter');
   row[x]=(row[x]+v)&255;
  }
  for(let x=0;x<w;x++){if(channels===4)alpha[y*w+x]=row[x*4+3];row.copy(out,(y*w+x)*3,x*channels,x*channels+3);}prev=row;
 }
 return {w,h,pixels:out,alpha};
}
function chunk(type,data) {const t=Buffer.from(type), size=Buffer.alloc(4),crc=Buffer.alloc(4);size.writeUInt32BE(data.length);crc.writeUInt32BE(crc32(Buffer.concat([t,data])));return Buffer.concat([size,t,data,crc]);}
function encode(w,h,pixels){const header=Buffer.alloc(13);header.writeUInt32BE(w);header.writeUInt32BE(h,4);header[8]=8;header[9]=2;const raw=Buffer.alloc((w*3+1)*h);for(let y=0;y<h;y++)pixels.copy(raw,y*(w*3+1)+1,y*w*3,(y+1)*w*3);return Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(raw,{level:9})),chunk('IEND',Buffer.alloc(0))]);}
const source=fs.readFileSync('artifacts/gathering/wall.png'),generated=fs.readFileSync('artifacts/gathering/wall-v20.png');
if(sha(source)!=='6497f76c8a44bb0c7e9080bb7059b57580d4947e02713930d54758b4028aa3be')throw Error('wrong ancestor');
const old=decode(source),gen=decode(generated);
if(old.w!==1254||old.h!==1254)throw Error('size changed');
const result=Buffer.from(old.pixels),rect=[650,50,95,100];
const [left,top,width,height]=rect;
let x0=gen.w,y0=gen.h,x1=0,y1=0;
for(let y=0;y<gen.h;y++)for(let x=0;x<gen.w;x++)if(gen.alpha[y*gen.w+x]>180){x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);}
if(x1<=x0||y1<=y0)throw Error('missing opaque generated pigment');
// Area-average only opaque generated pigment. Remove translucent glow and map
// the pigment to charcoal/red ochre, allowing the original stone grain through.
for(let dy=0;dy<height;dy++)for(let dx=0;dx<width;dx++){
 const sx0=x0+Math.floor(dx*(x1-x0+1)/width), sx1=Math.max(sx0+1,x0+Math.floor((dx+1)*(x1-x0+1)/width));
 const sy0=y0+Math.floor(dy*(y1-y0+1)/height), sy1=Math.max(sy0+1,y0+Math.floor((dy+1)*(y1-y0+1)/height));
 let amount=0,red=0,green=0,blue=0;
 for(let sy=sy0;sy<sy1;sy++)for(let sx=sx0;sx<sx1;sx++){
  const a=gen.alpha[sy*gen.w+sx];if(a<=180)continue;
  const j=(sy*gen.w+sx)*3,r=gen.pixels[j],g=gen.pixels[j+1],b=gen.pixels[j+2];
  const pigment=r>g*1.5&&r>60?[143,62,29]:[24,19,15];
  const opacity=(a/255)*0.8; amount+=opacity;red+=opacity*pigment[0];green+=opacity*pigment[1];blue+=opacity*pigment[2];
 }
 if(!amount)continue;
 const opacity=amount/((sx1-sx0)*(sy1-sy0));const pigment=[red/amount,green/amount,blue/amount];const i=((top+dy)*old.w+left+dx)*3;
 for(let c=0;c<3;c++)result[i+c]=Math.round(old.pixels[i+c]*(1-opacity)+pigment[c]*opacity);
}
let changed=0,outside=0;
for(let y=0;y<old.h;y++)for(let x=0;x<old.w;x++){const i=(y*old.w+x)*3;if(!result.subarray(i,i+3).equals(old.pixels.subarray(i,i+3))){changed++;if(x<left||x>=left+width||y<top||y>=top+height)outside++;}}
if(!changed||outside)throw Error('preservation failed');
const wall=encode(old.w,old.h,result);
fs.writeFileSync('artifacts/gathering/wall-v20.png',wall);
fs.writeFileSync('artifacts/gathering/wall.png',wall);
const review={source_record:18,record_number:19,source_sha256:sha(source),generated_sha256:sha(generated),wall_sha256:sha(wall),png_dimensions:[old.w,old.h],png_format:'8-bit RGB PNG',png_bytes:wall.length,generated_dimensions:[gen.w,gen.h],motif_crop:[x0,y0,x1,y1],addition_rectangle:rect,changed_pixels:changed,changed_pixels_outside_rectangle:outside,method:'Built-in imagegen transparent pigment insert; translucent glow discarded, opaque pigment area-averaged into earth colours over vacant rock. Original pixels preserved everywhere else.',visual_review:'pending final inspection'};
fs.writeFileSync('gathering/checks/round-19/image-preservation.json',JSON.stringify(review,null,2)+'\n');
console.log(JSON.stringify(review));
