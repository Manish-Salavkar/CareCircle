import { useEffect, useState } from 'react'
import { Calendar, Loader2, Phone, Pill, X } from 'lucide-react'
import { getDefaultInputTime, getTodayInputDate } from '../utils/date'

const TASK_TYPE_OPTIONS = [
  { value: 'medicine', label: 'Medicine', Icon: Pill },
  { value: 'appointment', label: 'Appointment', Icon: Calendar },
  { value: 'check_in', label: 'Check-in', Icon: Phone },
]

export function AddTaskModal({ careRecipientName, onClose, onSubmit }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [taskType, setTaskType] = useState('medicine')
  const [dueDate, setDueDate] = useState(getTodayInputDate)
  const [dueTime, setDueTime] = useState(getDefaultInputTime)

  const [validationErrors, setValidationErrors] = useState({})
  const [submitError, setSubmitError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && !isSubmitting) onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isSubmitting, onClose])

  const handleFormSubmit = async (event) => {
    event.preventDefault()
    if (isSubmitting) return

    const errors = {}
    const trimmedTitle = title.trim()

    if (!trimmedTitle) {
      errors.title = 'Please enter a task title.'
    } else if (trimmedTitle.length > 255) {
      errors.title = 'Task title must be 255 characters or fewer.'
    }

    if (!dueDate) errors.dueDate = 'Please select a due date.'
    if (!dueTime) errors.dueTime = 'Please select a due time.'

    let dueAtIso = ''
    if (dueDate && dueTime) {
      const [year, month, day] = dueDate.split('-').map(Number)
      const [hours, minutes] = dueTime.split(':').map(Number)
      const localDateTime = new Date(year, month - 1, day, hours, minutes, 0, 0)
      if (Number.isNaN(localDateTime.getTime())) {
        errors.dueDate = 'Please enter a valid date and time.'
      } else {
        dueAtIso = localDateTime.toISOString()
      }
    }

    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors)
      return
    }

    setValidationErrors({})
    setSubmitError(null)
    setIsSubmitting(true)

    try {
      const trimmedDescription = description.trim()
      await onSubmit({
        title: trimmedTitle,
        description: trimmedDescription || null,
        task_type: taskType,
        due_at: dueAtIso,
      })
      onClose()
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : 'Unable to create task. Please try again.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-task-title"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isSubmitting) onClose()
      }}
    >
      <div className="w-full max-w-lg rounded-t-2xl border border-[#EAEAEA] bg-white p-5 shadow-lg sm:rounded-2xl sm:p-6">
        <div className="flex items-start justify-between gap-4 border-b border-[#EAEAEA] pb-4">
          <div>
            <h2 id="add-task-title" className="text-lg font-semibold text-[#171717]">
              Add Care Task
            </h2>
            {careRecipientName && (
              <p className="mt-0.5 text-xs text-[#737373]">
                For {careRecipientName}
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Close modal"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-transparent text-[#737373] transition-colors hover:bg-neutral-100 hover:text-[#171717] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:opacity-50"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={handleFormSubmit} noValidate className="mt-4 space-y-4">
          {submitError && (
            <div
              role="alert"
              className="rounded-xl border border-[#FECACA] bg-[#FEF2F2] px-3.5 py-2.5 text-sm text-[#991B1B]"
            >
              {submitError}
            </div>
          )}

          <div>
            <label
              htmlFor="task-title-input"
              className="mb-1.5 block text-sm font-medium text-[#171717]"
            >
              Task title <span className="text-[#B91C1C]">*</span>
            </label>
            <input
              id="task-title-input"
              type="text"
              required
              autoFocus
              value={title}
              onChange={(e) => {
                setTitle(e.target.value)
                if (validationErrors.title) {
                  setValidationErrors((prev) => ({ ...prev, title: '' }))
                }
              }}
              placeholder="e.g., Evening blood pressure medication"
              disabled={isSubmitting}
              className="min-h-[44px] w-full rounded-xl border border-[#EAEAEA] bg-white px-3.5 py-2 text-sm text-[#171717] placeholder:text-[#737373]/70 focus:border-[#171717] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:bg-neutral-50"
            />
            {validationErrors.title && (
              <p className="mt-1 text-xs font-medium text-[#B91C1C]">
                {validationErrors.title}
              </p>
            )}
          </div>

          <div>
            <span className="mb-1.5 block text-sm font-medium text-[#171717]">
              Task type <span className="text-[#B91C1C]">*</span>
            </span>
            <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Task type">
              {TASK_TYPE_OPTIONS.map(({ value, label, Icon }) => {
                const selected = taskType === value
                return (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    disabled={isSubmitting}
                    onClick={() => setTaskType(value)}
                    className={`inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border px-2.5 py-2 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] sm:text-sm ${
                      selected
                        ? 'border-[#171717] bg-[#171717] text-white'
                        : 'border-[#EAEAEA] bg-white text-[#171717] hover:bg-neutral-50'
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>{label}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label
                htmlFor="task-due-date-input"
                className="mb-1.5 block text-sm font-medium text-[#171717]"
              >
                Due date <span className="text-[#B91C1C]">*</span>
              </label>
              <input
                id="task-due-date-input"
                type="date"
                required
                value={dueDate}
                onChange={(e) => {
                  setDueDate(e.target.value)
                  if (validationErrors.dueDate) {
                    setValidationErrors((prev) => ({ ...prev, dueDate: '' }))
                  }
                }}
                disabled={isSubmitting}
                className="min-h-[44px] w-full rounded-xl border border-[#EAEAEA] bg-white px-3.5 py-2 text-sm text-[#171717] focus:border-[#171717] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:bg-neutral-50"
              />
              {validationErrors.dueDate && (
                <p className="mt-1 text-xs font-medium text-[#B91C1C]">
                  {validationErrors.dueDate}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="task-due-time-input"
                className="mb-1.5 block text-sm font-medium text-[#171717]"
              >
                Due time <span className="text-[#B91C1C]">*</span>
              </label>
              <input
                id="task-due-time-input"
                type="time"
                required
                value={dueTime}
                onChange={(e) => {
                  setDueTime(e.target.value)
                  if (validationErrors.dueTime) {
                    setValidationErrors((prev) => ({ ...prev, dueTime: '' }))
                  }
                }}
                disabled={isSubmitting}
                className="min-h-[44px] w-full rounded-xl border border-[#EAEAEA] bg-white px-3.5 py-2 text-sm text-[#171717] focus:border-[#171717] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:bg-neutral-50"
              />
              {validationErrors.dueTime && (
                <p className="mt-1 text-xs font-medium text-[#B91C1C]">
                  {validationErrors.dueTime}
                </p>
              )}
            </div>
          </div>

          <div>
            <label
              htmlFor="task-description-input"
              className="mb-1.5 block text-sm font-medium text-[#171717]"
            >
              Description <span className="font-normal text-[#737373]">(optional)</span>
            </label>
            <textarea
              id="task-description-input"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Dosage, doctor name, or notes for the family..."
              disabled={isSubmitting}
              className="w-full rounded-xl border border-[#EAEAEA] bg-white px-3.5 py-2.5 text-sm text-[#171717] placeholder:text-[#737373]/70 focus:border-[#171717] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:bg-neutral-50"
            />
          </div>

          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-[#EAEAEA] bg-white px-4 py-2 text-sm font-medium text-[#171717] transition-colors hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-[#171717] px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-[#262626] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting && (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              <span>{isSubmitting ? 'Adding Task...' : 'Create Task'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

