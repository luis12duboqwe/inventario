// [PACK25-SKELETON-START]
export function Skeleton({ lines=5 }: { lines?: number }) {
  return (
    <div aria-busy="true">
      {Array.from({length: lines}).map((_,i)=>(
        <div key={i} style={{height:12, margin:'10px 0', borderRadius:6, opacity:.35, background:'linear-gradient(90deg,#9993,#9996,#9993)'}}/>
      ))}
    </div>
  );
}
// [PACK25-SKELETON-END]
