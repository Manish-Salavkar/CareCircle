import { CheckCircle2, Clock, Sparkles } from 'lucide-react'

const EMPTY_COPY = {
  overdue: {
    title: 'No overdue tasks',
    description: 'Everything from earlier is caught up.',
    Icon: Sparkles,
  },
  due: {
    title: 'No remaining tasks due today',
    description: 'Add a task if something else comes up today.',
    Icon: Clock,
  },
  done: {
    title: 'No tasks completed yet today',
    description: 'Completed tasks will appear here with who finished them.',
    Icon: CheckCircle2,
  },
}

export function EmptyState({ variant }) {
  const { title, description, Icon } = EMPTY_COPY[variant]

  return (
    <div className="flex items-center gap-3 rounded-2xl border border-dashed border-[#EAEAEA] bg-white px-4 py-5">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-[#EAEAEA] bg-neutral-50">
        <Icon className="h-4 w-4 text-[#737373]" aria-hidden="true" />
      </div>
      <div>
        <p className="text-sm font-medium text-[#171717]">{title}</p>
        <p className="text-xs text-[#737373]">{description}</p>
      </div>
    </div>
  )
}

