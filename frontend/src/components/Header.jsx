import { AlertCircle, HeartHandshake, Plus, RefreshCw, User } from 'lucide-react'
import { formatDashboardDate, getFriendlyGreeting, getTodayInputDate } from '../utils/date'

export function Header({
  dateIso,
  careRecipientName,
  familyMembers,
  isLoadingMembers,
  membersError,
  selectedMemberId,
  onSelectMember,
  onRetryMembers,
  onOpenAddTask,
  canAddTask,
}) {
  const activeMember = familyMembers.find((m) => m.id === selectedMemberId)
  const greeting = getFriendlyGreeting()
  const formattedDate = formatDashboardDate(dateIso ?? getTodayInputDate())

  return (
    <header className="border-b border-[#EAEAEA] bg-white">
      <div className="mx-auto max-w-3xl px-4 py-5 sm:px-6 sm:py-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#EAEAEA] bg-white shadow-2xs">
              <HeartHandshake className="h-4 w-4 text-[#171717]" aria-hidden="true" />
            </div>
            <span className="text-base font-semibold tracking-tight text-[#171717]">
              CareCircle
            </span>
          </div>

          <button
            type="button"
            onClick={onOpenAddTask}
            disabled={!canAddTask}
            className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-[#171717] px-4 py-2 text-sm font-medium text-white shadow-2xs transition-colors hover:bg-[#262626] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            <span>Add Task</span>
          </button>
        </div>

        <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-[#737373]">{formattedDate}</p>
            <h1 className="text-2xl font-semibold tracking-tight text-[#171717] sm:text-3xl">
              {greeting}
              {activeMember ? `, ${activeMember.name}` : ''}
            </h1>
            {careRecipientName && (
              <p className="text-sm text-[#737373]">
                Coordinating daily care for{' '}
                <span className="font-medium text-[#171717]">{careRecipientName}</span>
              </p>
            )}
          </div>

          <div className="w-full sm:w-auto sm:min-w-[220px]">
            <label
              htmlFor="family-member-select"
              className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-[#737373]"
            >
              <User className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Acting as (demo member)</span>
            </label>

            {membersError ? (
              <div className="flex min-h-[44px] items-center justify-between gap-2 rounded-xl border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-xs text-[#991B1B]">
                <span className="flex items-center gap-1.5">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  <span>Failed to load</span>
                </span>
                <button
                  type="button"
                  onClick={onRetryMembers}
                  className="inline-flex items-center gap-1 font-medium underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#991B1B]"
                >
                  <RefreshCw className="h-3 w-3" aria-hidden="true" />
                  Retry
                </button>
              </div>
            ) : (
              <select
                id="family-member-select"
                value={selectedMemberId}
                onChange={(e) => onSelectMember(e.target.value)}
                disabled={isLoadingMembers || familyMembers.length === 0}
                className="min-h-[44px] w-full rounded-xl border border-[#EAEAEA] bg-white px-3.5 py-2 text-sm font-medium text-[#171717] shadow-2xs transition-colors focus:border-[#171717] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:cursor-not-allowed disabled:bg-neutral-50 disabled:text-[#737373]"
              >
                {isLoadingMembers ? (
                  <option value="">Loading family members...</option>
                ) : familyMembers.length === 0 ? (
                  <option value="">No family members found</option>
                ) : (
                  familyMembers.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.name} ({member.relationship})
                    </option>
                  ))
                )}
              </select>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

