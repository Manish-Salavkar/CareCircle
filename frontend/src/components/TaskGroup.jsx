import { EmptyState } from './EmptyState'
import { TaskCard } from './TaskCard'

const BADGE_STYLE = {
  overdue: 'border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C]',
  due: 'border-[#EAEAEA] bg-neutral-50 text-[#171717]',
  done: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
}

export function TaskGroup({
  title,
  variant,
  tasks,
  todayIsoDate,
  completingTaskIds,
  canComplete,
  onMarkDone,
}) {
  const headingId = `section-${variant}`

  return (
    <section aria-labelledby={headingId} className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <h2 id={headingId} className="text-lg font-semibold tracking-tight text-[#171717]">
            {title}
          </h2>
          <span
            className={`inline-flex min-w-[26px] items-center justify-center rounded-full border px-2 py-0.5 text-xs font-semibold ${BADGE_STYLE[variant]}`}
          >
            {tasks.length}
          </span>
        </div>
      </div>

      {tasks.length === 0 ? (
        <EmptyState variant={variant} />
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              todayIsoDate={todayIsoDate}
              isCompleting={Boolean(completingTaskIds[task.id])}
              canComplete={canComplete}
              onMarkDone={onMarkDone}
            />
          ))}
        </div>
      )}
    </section>
  )
}

