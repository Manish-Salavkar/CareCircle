export function getFriendlyGreeting(date = new Date()) {
  const hour = date.getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

export function formatDashboardDate(isoDate) {
  const [year, month, day] = isoDate.split('-').map(Number)
  if (!year || !month || !day) return isoDate

  return new Intl.DateTimeFormat(undefined, {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  }).format(new Date(year, month - 1, day))
}

export function formatTime(isoDatetime) {
  const date = new Date(isoDatetime)
  if (Number.isNaN(date.getTime())) return isoDatetime

  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

export function formatDueLabel(isoDatetime, todayIsoDate) {
  const date = new Date(isoDatetime)
  if (Number.isNaN(date.getTime())) return isoDatetime

  const localIsoDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  const timeText = formatTime(isoDatetime)

  if (todayIsoDate && localIsoDate === todayIsoDate) {
    return `Today, ${timeText}`
  }

  const dateText = new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
  }).format(date)

  return `${dateText}, ${timeText}`
}

export function formatLateBy(dueAtIso, now = new Date()) {
  const due = new Date(dueAtIso)
  if (Number.isNaN(due.getTime())) return null

  const diffMs = now.getTime() - due.getTime()
  if (diffMs <= 0) return null

  const totalMinutes = Math.max(1, Math.floor(diffMs / 60000))
  if (totalMinutes < 60) return `${totalMinutes}m late`

  const totalHours = Math.floor(totalMinutes / 60)
  if (totalHours < 24) {
    const remainingMinutes = totalMinutes % 60
    return remainingMinutes > 0 ? `${totalHours}h ${remainingMinutes}m late` : `${totalHours}h late`
  }

  const totalDays = Math.floor(totalHours / 24)
  return totalDays === 1 ? '1 day late' : `${totalDays} days late`
}

export function getTodayInputDate() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

export function getDefaultInputTime() {
  const next = new Date(Date.now() + 60 * 60 * 1000)
  next.setMinutes(0, 0, 0)
  return `${String(next.getHours()).padStart(2, '0')}:00`
}

