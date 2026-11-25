export function SummaryCards({ counts }) {
  const hasOverdue = counts.overdue > 0

  return (
    <section aria-label="Today summary" className="grid grid-cols-3 gap-3 sm:gap-4">
      <div
        className={`rounded-2xl border p-4 shadow-2xs sm:p-5 ${
          hasOverdue
            ? 'border-[#FECACA] bg-[#FEF2F2]'
            : 'border-[#EAEAEA] bg-white'
        }`}
      >
        <p
          className={`text-xs font-medium sm:text-sm ${
            hasOverdue ? 'text-[#991B1B]' : 'text-[#737373]'
          }`}
        >
          Overdue
        </p>
        <p
          className={`mt-1 text-2xl font-semibold tracking-tight sm:text-3xl ${
            hasOverdue ? 'text-[#B91C1C]' : 'text-[#171717]'
          }`}
        >
          {counts.overdue}
        </p>
      </div>

      <div className="rounded-2xl border border-[#EAEAEA] bg-white p-4 shadow-2xs sm:p-5">
        <p className="text-xs font-medium text-[#737373] sm:text-sm">Due today</p>
        <p className="mt-1 text-2xl font-semibold tracking-tight text-[#171717] sm:text-3xl">
          {counts.due}
        </p>
      </div>

      <div className="rounded-2xl border border-[#BBF7D0] bg-[#F0FDF4] p-4 shadow-2xs sm:p-5">
        <p className="text-xs font-medium text-[#166534] sm:text-sm">Completed</p>
        <p className="mt-1 text-2xl font-semibold tracking-tight text-[#15803D] sm:text-3xl">
          {counts.done}
        </p>
      </div>
    </section>
  )
}

