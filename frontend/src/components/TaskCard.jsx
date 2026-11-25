import {
  Calendar,
  Check,
  CheckCircle2,
  Clock,
  Loader2,
  Phone,
  Pill,
} from 'lucide-react'
import { formatDueLabel, formatLateBy, formatTime } from '../utils/date'

const TASK_TYPE_META = {
  medicine: { label: 'Medicine', Icon: Pill },
  appointment: { label: 'Appointment', Icon: Calendar },
  check_in: { label: 'Check-in', Icon: Phone },
}

export function TaskCard({
  task,
  todayIsoDate,
  isCompleting,
  canComplete,
  onMarkDone,
}) {
  const { label: typeLabel, Icon: TypeIcon } = TASK_TYPE_META[task.task_type]
  const isDone = task.status === 'done'
  const isOverdue = !isDone && task.is_overdue
  const lateLabel = isOverdue ? formatLateBy(task.due_at) : null

  const cardClasses = isDone
    ? 'border-[#DCFCE7] bg-[#F0FDF4]/60'
    : isOverdue
      ? 'border-[#FECACA] bg-[#FEF2F2]/50'
      : 'border-[#EAEAEA] bg-white'

  return (
    <article
      className={`rounded-2xl border p-4 shadow-2xs transition-colors sm:p-5 ${cardClasses}`}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#EAEAEA] bg-white px-2.5 py-0.5 text-xs font-medium text-[#171717]">
              <TypeIcon className="h-3.5 w-3.5 text-[#737373]" aria-hidden="true" />
              {typeLabel}
            </span>

            {isDone ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-[#BBF7D0] bg-[#F0FDF4] px-2.5 py-0.5 text-xs font-medium text-[#166534]">
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                Done
              </span>
            ) : isOverdue ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-[#FECACA] bg-[#FEF2F2] px-2.5 py-0.5 text-xs font-medium text-[#B91C1C]">
                {lateLabel ? `Overdue · ${lateLabel}` : 'Overdue'}
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full border border-[#EAEAEA] bg-neutral-50 px-2.5 py-0.5 text-xs font-medium text-[#737373]">
                Pending
              </span>
            )}
          </div>

          <div>
            <h3 className="text-base font-semibold leading-snug text-[#171717]">
              {task.title}
            </h3>
            {task.description && (
              <p className="mt-1 text-sm leading-relaxed text-[#737373]">
                {task.description}
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#737373]">
            <span className="inline-flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" aria-hidden="true" />
              <span className={isOverdue ? 'font-medium text-[#991B1B]' : undefined}>
                Due {formatDueLabel(task.due_at, todayIsoDate)}
              </span>
            </span>

            {isDone && task.completed_at && (
              <span className="inline-flex items-center gap-1.5 font-medium text-[#166534]">
                <Check className="h-3.5 w-3.5" aria-hidden="true" />
                <span>
                  Completed
                  {task.completed_by_name ? ` by ${task.completed_by_name}` : ''} at{' '}
                  {formatTime(task.completed_at)}
                </span>
              </span>
            )}
          </div>
        </div>

        {!isDone && (
          <div className="shrink-0 pt-1 sm:pt-0">
            <button
              type="button"
              onClick={() => onMarkDone(task.id)}
              disabled={isCompleting || !canComplete}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl border border-[#EAEAEA] bg-white px-4 py-2 text-sm font-medium text-[#171717] shadow-2xs transition-colors hover:border-[#171717] hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
            >
              {isCompleting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Check className="h-4 w-4" aria-hidden="true" />
                  <span>Mark as done</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </article>
  )
}

