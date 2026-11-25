import { AlertCircle, Loader2, RefreshCw, Send, Sparkles } from 'lucide-react'
import { useAssistant } from '../hooks/useAssistant'

export function AskTodayCard({ careRecipientId, careRecipientName }) {
  const {
    question,
    setQuestion,
    answer,
    isStreaming,
    error,
    lastSubmittedQuestion,
    submitQuestion,
    retryLastQuestion,
    clearError,
  } = useAssistant(careRecipientId)

  const handleSubmit = (event) => {
    event.preventDefault()
    void submitQuestion()
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (!isStreaming) void submitQuestion()
    }
  }

  const canSubmit = !isStreaming && question.trim().length > 0

  return (
    <section
      aria-labelledby="ask-about-today-heading"
      className="rounded-2xl border border-[#EAEAEA] bg-white p-4 shadow-2xs sm:p-5"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-[#EAEAEA] bg-neutral-50">
          <Sparkles className="h-4 w-4 text-[#171717]" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <h2
            id="ask-about-today-heading"
            className="text-base font-semibold tracking-tight text-[#171717]"
          >
            Ask about today
          </h2>
          <p className="mt-0.5 text-xs text-[#737373] sm:text-sm">
            Answers are based only on {careRecipientName ? `${careRecipientName}'s` : "today's"} care schedule.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-4 space-y-3" noValidate>
        <div>
          <label htmlFor="ask-today-input" className="sr-only">
            Ask a question about today&apos;s care schedule
          </label>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <textarea
              id="ask-today-input"
              rows={2}
              value={question}
              onChange={(e) => {
                setQuestion(e.target.value)
                if (error) clearError()
              }}
              onKeyDown={handleKeyDown}
              disabled={isStreaming}
              placeholder="What still needs to be done today?"
              className="w-full resize-none rounded-xl border border-[#EAEAEA] bg-white px-3.5 py-2.5 text-sm text-[#171717] placeholder:text-[#737373]/70 focus:border-[#171717] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:bg-neutral-50 disabled:text-[#737373]"
            />

            <button
              type="submit"
              disabled={!canSubmit}
              className="inline-flex min-h-[44px] w-full shrink-0 items-center justify-center gap-2 rounded-xl bg-[#171717] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#262626] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#171717] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
            >
              {isStreaming ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  <span>Answering...</span>
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" aria-hidden="true" />
                  <span>Send</span>
                </>
              )}
            </button>
          </div>
          <p className="mt-1.5 text-[11px] text-[#737373]">
            Press Enter to send, Shift+Enter for a new line.
          </p>
        </div>
      </form>

      {error && (
        <div
          role="alert"
          className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#FECACA] bg-[#FEF2F2] px-3.5 py-2.5 text-sm text-[#991B1B]"
        >
          <span className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </span>
          {lastSubmittedQuestion && !isStreaming && (
            <button
              type="button"
              onClick={() => void retryLastQuestion()}
              className="inline-flex items-center gap-1.5 text-xs font-semibold underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#991B1B]"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Retry
            </button>
          )}
        </div>
      )}

      {(isStreaming || answer) && (
        <div
          aria-live="polite"
          className="mt-3 rounded-xl border border-[#EAEAEA] bg-neutral-50/70 px-4 py-3 text-sm leading-relaxed text-[#171717]"
        >
          {answer ? (
            <p className="whitespace-pre-wrap">
              {answer}
              {isStreaming && (
                <span
                  aria-hidden="true"
                  className="ml-1 inline-block h-3.5 w-1.5 animate-pulse rounded-xs bg-[#171717] align-middle"
                />
              )}
            </p>
          ) : (
            <span className="inline-flex items-center gap-2 text-[#737373]">
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              <span>Checking today&apos;s schedule...</span>
            </span>
          )}
        </div>
      )}
    </section>
  )
}

