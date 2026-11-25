import { useCallback, useEffect, useRef, useState } from 'react'
import { askAssistantStream } from '../services/api'

export function useAssistant(careRecipientId) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState(null)
  const [lastSubmittedQuestion, setLastSubmittedQuestion] = useState('')

  const abortRef = useRef(null)
  const streamingRef = useRef(false)

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  const clearError = useCallback(() => setError(null), [])

  const submitQuestion = useCallback(
    async (overrideQuestion) => {
      if (streamingRef.current) return

      const trimmed = (overrideQuestion ?? question).trim()
      if (!trimmed) {
        setError('Please enter a question about today’s schedule.')
        return
      }

      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      streamingRef.current = true
      setIsStreaming(true)
      setError(null)
      setAnswer('')
      setLastSubmittedQuestion(trimmed)

      try {
        await askAssistantStream(
          {
            question: trimmed,
            ...(careRecipientId ? { care_recipient_id: careRecipientId } : {}),
          },
          {
            onToken: (chunk) => setAnswer((prev) => prev + chunk),
          },
          controller.signal,
        )
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return
        setError(
          err instanceof Error
            ? err.message
            : 'Unable to get an answer right now. Please try again.',
        )
      } finally {
        streamingRef.current = false
        if (!controller.signal.aborted) setIsStreaming(false)
      }
    },
    [question, careRecipientId],
  )

  const retryLastQuestion = useCallback(async () => {
    if (!lastSubmittedQuestion) return
    await submitQuestion(lastSubmittedQuestion)
  }, [lastSubmittedQuestion, submitQuestion])

  return {
    question,
    setQuestion,
    answer,
    isStreaming,
    error,
    lastSubmittedQuestion,
    submitQuestion,
    retryLastQuestion,
    clearError,
  }
}

