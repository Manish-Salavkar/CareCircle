export function LoadingState() {
  return (
    <div className="space-y-8" role="status" aria-label="Loading today's care tasks">
      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        {[0, 1, 2].map((item) => (
          <div
            key={item}
            className="h-22 animate-pulse rounded-2xl border border-[#EAEAEA] bg-neutral-50"
          />
        ))}
      </div>

      {[0, 1].map((section) => (
        <div key={section} className="space-y-3">
          <div className="h-6 w-36 animate-pulse rounded-lg bg-neutral-100" />
          <div className="h-28 animate-pulse rounded-2xl border border-[#EAEAEA] bg-neutral-50" />
          <div className="h-28 animate-pulse rounded-2xl border border-[#EAEAEA] bg-neutral-50" />
        </div>
      ))}
    </div>
  )
}

