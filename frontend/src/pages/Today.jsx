import { useState } from 'react'
import { AlertCircle, RefreshCw, X } from 'lucide-react'
import { AddTaskModal } from '../components/AddTaskModal'
import { AskTodayCard } from '../components/AskTodayCard'
import { Header } from '../components/Header'
import { LoadingState } from '../components/LoadingState'
import { SummaryCards } from '../components/SummaryCards'
import { TaskGroup } from '../components/TaskGroup'
import { useToday } from '../hooks/useToday'

export function Today() {
  const {
    today,
    isLoadingToday,
    todayError,
    familyMembers,
    isLoadingMembers,
    membersError,
    selectedMemberId,
    setSelectedMemberId,
    completingTaskIds,
    actionFeedback,
    clearActionFeedback,
    refetchToday,
    refetchMembers,
    markTaskDone,
    addTask,
  } = useToday()

  const [isAddModalOpen, setIsAddModalOpen] = useState(false)

  const canAddTask = Boolean(today?.care_recipient_id ?? familyMembers[0]?.care_recipient_id)
  const canComplete = Boolean(selectedMemberId) && !isLoadingMembers && !membersError

  return (
    <div className="min-h-screen bg-white text-[#171717]">
      <Header
        dateIso={today?.date}
        careRecipientName={today?.care_recipient_name}
        familyMembers={familyMembers}
        isLoadingMembers={isLoadingMembers}
        membersError={membersError}
        selectedMemberId={selectedMemberId}
        onSelectMember={setSelectedMemberId}
        onRetryMembers={() => void refetchMembers()}
        onOpenAddTask={() => setIsAddModalOpen(true)}
        canAddTask={canAddTask}
      />

      <main className="mx-auto max-w-3xl space-y-8 px-4 py-6 sm:px-6 sm:py-8">
        {actionFeedback && (
          <div
            role="alert"
            className={`flex items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-sm ${
              actionFeedback.type === 'error'
                ? 'border-[#FECACA] bg-[#FEF2F2] text-[#991B1B]'
                : 'border-[#EAEAEA] bg-neutral-50 text-[#171717]'
            }`}
          >
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{actionFeedback.message}</span>
            </div>
            <button
              type="button"
              onClick={clearActionFeedback}
              aria-label="Dismiss message"
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-black/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717]"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        )}

        {isLoadingToday && !today ? (
          <LoadingState />
        ) : todayError && !today ? (
          <div
            role="alert"
            className="rounded-2xl border border-[#FECACA] bg-[#FEF2F2] p-6 text-center"
          >
            <AlertCircle
              className="mx-auto h-7 w-7 text-[#B91C1C]"
              aria-hidden="true"
            />
            <h2 className="mt-3 text-base font-semibold text-[#171717]">
              Unable to load today&apos;s care tasks
            </h2>
            <p className="mt-1 text-sm text-[#737373]">{todayError}</p>
            <button
              type="button"
              onClick={() => void refetchToday()}
              className="mt-4 inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-[#171717] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#262626] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717]"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              <span>Try again</span>
            </button>
          </div>
        ) : today ? (
          <>
            {todayError && (
              <div
                role="alert"
                className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#FECACA] bg-[#FEF2F2] px-4 py-3 text-sm text-[#991B1B]"
              >
                <span>{todayError}</span>
                <button
                  type="button"
                  onClick={() => void refetchToday()}
                  className="inline-flex items-center gap-1.5 font-medium underline"
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                  Retry
                </button>
              </div>
            )}

            <SummaryCards counts={today.counts} />

            <AskTodayCard
              careRecipientId={today.care_recipient_id}
              careRecipientName={today.care_recipient_name}
            />

            <div className="space-y-8">
              <TaskGroup
                title="Overdue"
                variant="overdue"
                tasks={today.overdue}
                todayIsoDate={today.date}
                completingTaskIds={completingTaskIds}
                canComplete={canComplete}
                onMarkDone={(id) => void markTaskDone(id)}
              />

              <TaskGroup
                title="Due today"
                variant="due"
                tasks={today.due}
                todayIsoDate={today.date}
                completingTaskIds={completingTaskIds}
                canComplete={canComplete}
                onMarkDone={(id) => void markTaskDone(id)}
              />

              <TaskGroup
                title="Completed"
                variant="done"
                tasks={today.done}
                todayIsoDate={today.date}
                completingTaskIds={completingTaskIds}
                canComplete={canComplete}
                onMarkDone={(id) => void markTaskDone(id)}
              />
            </div>
          </>
        ) : null}
      </main>

      {isAddModalOpen && (
        <AddTaskModal
          careRecipientName={today?.care_recipient_name}
          onClose={() => setIsAddModalOpen(false)}
          onSubmit={addTask}
        />
      )}
    </div>
  )
}

