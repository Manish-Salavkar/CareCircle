const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').trim()
const API_BASE_URL = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readErrorMessage(response) {
  let message = `Request failed (${response.status})`
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') {
      return body.detail
    }
    if (Array.isArray(body?.detail) && body.detail.length > 0) {
      const first = body.detail[0]
      if (typeof first?.msg === 'string') {
        return first.msg
      }
    }
  } catch {
  }
  return message
}

async function request(path, init) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response))
  }

  return response.json()
}

export function fetchToday(careRecipientId, signal) {
  const query = careRecipientId
    ? `?care_recipient_id=${encodeURIComponent(careRecipientId)}`
    : ''
  return request(`/api/today${query}`, { signal })
}

export function fetchFamilyMembers(careRecipientId, signal) {
  const query = careRecipientId
    ? `?care_recipient_id=${encodeURIComponent(careRecipientId)}`
    : ''
  return request(`/api/family-members${query}`, { signal })
}

export function createTask(payload) {
  return request('/api/tasks', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function completeTask(taskId, payload) {
  return request(`/api/tasks/${encodeURIComponent(taskId)}/complete`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

function parseSseBlock(block) {
  const lines = block.split(/\r?\n/)
  let eventName = 'message'
  const dataLines = []

  for (const line of lines) {
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) {
      eventName = line.slice('event:'.length).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trimStart())
    }
  }

  if (dataLines.length === 0) return null

  try {
    return {
      event: eventName,
      data: JSON.parse(dataLines.join('\n')),
    }
  } catch {
    throw new Error('Received malformed event payload from assistant.')
  }
}

export async function askAssistantStream(payload, handlers, signal) {
  const response = await fetch(`${API_BASE_URL}/api/assistant/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(payload),
    signal,
  })

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response))
  }

  if (!response.body) {
    throw new Error('Streaming response body is unavailable.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let receivedDone = false

  const handleBlock = (rawBlock) => {
    const parsed = parseSseBlock(rawBlock)
    if (!parsed) return

    if (parsed.event === 'token') {
      if (typeof parsed.data?.chunk === 'string') {
        handlers.onToken(parsed.data.chunk)
      }
    } else if (parsed.event === 'done') {
      receivedDone = true
      handlers.onDone?.()
    } else if (parsed.event === 'error') {
      const detail = parsed.data?.detail
      throw new Error(
        typeof detail === 'string'
          ? detail
          : 'Assistant encountered an error while answering.',
      )
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      buffer += decoder.decode()
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split(/\r?\n\r?\n/)
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      if (part.trim()) {
        handleBlock(part)
      }
    }
  }

  if (buffer.trim()) {
    handleBlock(buffer)
  }

  if (!receivedDone) {
    throw new Error('Assistant response was interrupted before completing.')
  }
}

