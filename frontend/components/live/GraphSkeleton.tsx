"use client";

function SkeletonNode({ w = 24 }: { w?: number }) {
  return (
    <div className="w-[200px] h-[80px] rounded-xl border px-3.5 py-2.5 shrink-0" style={{ borderColor: "#3a3624", background: "#181c10" }}>
      <div className="flex items-center gap-2 mb-1.5">
        <div className="w-2.5 h-2.5 rounded-full" style={{ background: "#3a3624" }} />
        <div className="h-3 rounded" style={{ background: "#2e2b1c", width: `${w * 4}px` }} />
      </div>
      <div className="h-2 w-28 rounded mb-1.5" style={{ background: "#252314" }} />
      <div className="flex gap-3">
        <div className="h-2 w-8 rounded" style={{ background: "#252314" }} />
        <div className="h-2 w-8 rounded" style={{ background: "#252314" }} />
      </div>
    </div>
  );
}

function VLine() {
  return <div className="w-px h-6" style={{ background: "#3a3624" }} />;
}

export default function GraphSkeleton() {
  return (
    <div className="h-full overflow-hidden" style={{ background: "#151810" }}>
      <div className="flex flex-col items-center pt-10 animate-pulse">
        <SkeletonNode w={20} />
        <VLine />
        <div className="flex gap-10">
          {[18, 22, 16].map((w, i) => (
            <div key={i} className="flex flex-col items-center">
              <VLine />
              <SkeletonNode w={w} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
