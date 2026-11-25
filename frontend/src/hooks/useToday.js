import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  completeTask,
  createTask,
  fetchFamilyMembers,
  fetchToday,
} from '../services/api'

const MEMBER_STORAGE_KEY = 'carecircle_active_family_member_id'

function getSavedMemberId() {
  try {
    return window.sessionStorage.getItem(MEMBER_STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

function saveMemberId(memberId) {
  try {
    if (memberId) {
      window.sessionStorage.setItem(MEMBER_STORAGE_KEY, memberId)
    } else {
      window.sessionStorage.removeItem(MEMBER_STORAGE_KEY)
    }
  } catch {
  }
}

export function useToday() {
  const [today, setToday] = useState(null)
  const [isLoadingToday, setIsLoadingToday] = useState(true)
  const [todayError, setTodayError] = useState(null)

  const [familyMembers, setFamilyMembers] = useState([])
  const [isLoadingMembers, setIsLoadingMembers] = useState(true)
  const [membersError, setMembersError] = useState(null)

  const [selectedMemberId, setSelectedMemberIdState] = useState(getSavedMemberId)
  const [completingTaskIds, setCompletingTaskIds] = useState({})
  const [actionFeedback, setActionFeedback] = useState(null)

  const setSelectedMemberId = useCallback((id) => {
    setSelectedMemberIdState(id)
    saveMemberId(id)
  }, [])

  const clearActionFeedback = useCallback(() => {
    setActionFeedback(null)
  }, [])

  const loadToday = useCallback(async (signal) => {
    setIsLoadingToday(true)
    setTodayError(null)
    try {
      const data = await fetchToday(undefined, signal)
      setToday(data)
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return
      setTodayError(err instanceof Error ? err.message : 'Failed to load today tasks.')
    } finally {
      if (!signal?.aborted) setIsLoadingToday(false)
    }
  }, [])

  const loadMembers = useCallback(async (signal) => {
    setIsLoadingMembers(true)
    setMembersError(null)
    try {
      const members = await fetchFamilyMembers(undefined, signal)
      setFamilyMembers(members)
      setSelectedMemberIdState((current) => {
        const stored = current || getSavedMemberId()
        const match = members.find((m) => m.id === stored)
        const resolved = match ? match.id : (members[0]?.id ?? '')
        saveMemberId(resolved)
        return resolved
      })
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return
      setMembersError(err instanceof Error ? err.message : 'Failed to load family members.')
    } finally {
      if (!signal?.aborted) setIsLoadingMembers(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    fetchToday(undefined, controller.signal)
      .then((data) => {
        setToday(data)
        setTodayError(null)
      })
      .catch((err) => {
        if (err instanceof Error && err.name === 'AbortError') return
        setTodayError(err instanceof Error ? err.message : 'Failed to load today tasks.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoadingToday(false)
      })

    fetchFamilyMembers(undefined, controller.signal)
      .then((members) => {
        setFamilyMembers(members)
        setMembersError(null)
        setSelectedMemberIdState((current) => {
          const stored = current || getSavedMemberId()
          const match = members.find((m) => m.id === stored)
          const resolved = match ? match.id : (members[0]?.id ?? '')
          saveMemberId(resolved)
          return resolved
        })
      })
      .catch((err) => {
        if (err instanceof Error && err.name === 'AbortError') return
        setMembersError(err instanceof Error ? err.message : 'Failed to load family members.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoadingMembers(false)
      })

    return () => controller.abort()
  }, [])

  const refetchToday = useCallback(() => loadToday(), [loadToday])
  const refetchMembers = useCallback(() => loadMembers(), [loadMembers])

  const markTaskDone = useCallback(
    async (taskId) => {
      if (!selectedMemberId) {
        setActionFeedback({
          type: 'error',
          message: 'Please select a family member before completing a task.',
        })
        return
      }
      if (completingTaskIds[taskId]) return

      setActionFeedback(null)
      setCompletingTaskIds((prev) => ({ ...prev, [taskId]: true }))

      try {
        await completeTask(taskId, { completed_by_id: selectedMemberId })
        await loadToday()
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          setActionFeedback({
            type: 'info',
            message: 'This task was already marked done. Dashboard refreshed.',
          })
          await loadToday()
        } else {
          setActionFeedback({
            type: 'error',
            message: err instanceof Error ? err.message : 'Unable to complete task.',
          })
        }
      } finally {
        setCompletingTaskIds((prev) => {
          const next = { ...prev }
          delete next[taskId]
          return next
        })
      }
    },
    [selectedMemberId, completingTaskIds, loadToday],
  )

  const addTask = useCallback(
    async (payload) => {
      const careRecipientId = today?.care_recipient_id ?? familyMembers[0]?.care_recipient_id
      if (!careRecipientId) {
        throw new Error('Care recipient context is not available yet.')
      }

      await createTask({ ...payload, care_recipient_id: careRecipientId })
      setActionFeedback(null)
      await loadToday()
    },
    [today?.care_recipient_id, familyMembers, loadToday],
  )

  return {
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
  }
}

