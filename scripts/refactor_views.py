import os

BASE = r"D:\study\大三\26春 软件工程创新实践\前端\postop-mgmt-frontend"

# ── 1. ChatView.vue ──
path = os.path.join(BASE, 'src', 'views', 'patient', 'ChatView.vue')
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Replace recording refs + functions with composable
old_rec = """const isRecording = ref(false)
const recordingSeconds = ref(0)
let mediaRecorder: MediaRecorder | null = null
let recordedChunks: Blob[] = []
let recordingTimer: ReturnType<typeof setInterval> | null = null"""

new_rec = """const voiceRecorder = useVoiceRecorder(async (blob, seconds) => {
  const file = new File([blob], 'recording.webm', { type: 'audio/webm' })
  await handleVoiceResult(file, seconds)
})
const { isRecording, recordingSeconds, toggleRecording, stopRecording, formatTime } = voiceRecorder"""
c = c.replace(old_rec, new_rec)

# Add import
c = c.replace(
    "import { useWebSocket } from '@/composables/useWebSocket'",
    "import { useWebSocket } from '@/composables/useWebSocket'\nimport { useVoiceRecorder } from '@/composables/useVoiceRecorder'"
)

# Remove old toggleRecording function
old_toggle = """async function toggleRecording() {
  if (isRecording.value) {
    stopRecording()
  } else {
    await startRecording()
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    recordedChunks = []

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordedChunks.push(e.data)
    }

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(recordedChunks, { type: 'audio/webm' })
      await handleVoiceResult(blob)
    }

    mediaRecorder.start()
    isRecording.value = true
    recordingSeconds.value = 0
    recordingTimer = setInterval(() => {
      recordingSeconds.value++
      // Auto-stop at 60s
      if (recordingSeconds.value >= 60) stopRecording()
    }, 1000)
  } catch {
    ElMessage.error('无法访问麦克风，请检查权限设置')
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  isRecording.value = false
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }
}"""

new_toggle = ""
c = c.replace(old_toggle, new_toggle)

# Update handleVoiceResult signature to accept seconds
c = c.replace(
    "async function handleVoiceResult(blob: Blob) {",
    "async function handleVoiceResult(blob: Blob, seconds = 0) {"
)
c = c.replace(
    "content: `[语音 ${recordingSeconds.value}\"] 正在识别...`,",
    "content: `[语音 ${seconds}\"] 正在识别...`,"
)
c = c.replace(
    "stopRecording()\n  disconnect()",
    "voiceRecorder.stopRecording()\n  disconnect()"
)

# Remove formatTime (now in composable)
# Actually keep the local fallback, the composable's formatTime is already destructured

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print("1. ChatView.vue refactored")

# ── 2. Doctor MessagesView.vue ──
path = os.path.join(BASE, 'src', 'views', 'doctor', 'MessagesView.vue')
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Replace recording refs
old_rec2 = """const imageInput = ref<HTMLInputElement>()
const uploadingMedia = ref(false)
const isRecording = ref(false)
const recordingSeconds = ref(0)
let mediaRecorder: MediaRecorder | null = null
let recordedChunks: Blob[] = []
let recordingTimer: ReturnType<typeof setInterval> | null = null"""

new_rec2 = """const imageInput = ref<HTMLInputElement>()
const uploadingMedia = ref(false)
const voiceRecorder = useVoiceRecorder(async (blob) => {
  const file = new File([blob], 'recording.webm', { type: 'audio/webm' })
  uploadingMedia.value = true
  try {
    const res = await doctorService.uploadVoice(file)
    if (res.data.success) await sendMessage('voice', res.data.url)
  } catch { ElMessage.error('语音上传失败') }
  finally { uploadingMedia.value = false }
})
const { isRecording, recordingSeconds, toggleRecording, stopRecording, formatTime } = voiceRecorder"""
c = c.replace(old_rec2, new_rec2)

# Add import
c = c.replace(
    "import { isHighRisk } from '@/utils/riskLevel'",
    "import { useVoiceRecorder } from '@/composables/useVoiceRecorder'\nimport { useMediaUrl } from '@/composables/useMediaUrl'"
)

# Replace apiBase + mediaSrc with composable
old_media = """const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function mediaSrc(url: string) {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return apiBase + url
}"""
c = c.replace(old_media, "const { mediaSrc } = useMediaUrl()")

# Remove old recording functions
old_funcs = """async function toggleRecording() {
  if (isRecording.value) stopRecording()
  else await startRecording()
}
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    recordedChunks = []
    mediaRecorder.ondataavailable = (e: any) => { if (e.data.size > 0) recordedChunks.push(e.data) }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(recordedChunks, { type: 'audio/webm' })
      const file = new File([blob], 'recording.webm', { type: 'audio/webm' })
      uploadingMedia.value = true
      try {
        const res = await doctorService.uploadVoice(file)
        if (res.data.success) await sendMessage('voice', res.data.url)
      } catch { ElMessage.error('语音上传失败') }
      finally { uploadingMedia.value = false }
    }
    mediaRecorder.start()
    isRecording.value = true
    recordingSeconds.value = 0
    recordingTimer = setInterval(() => { recordingSeconds.value++; if (recordingSeconds.value >= 60) stopRecording() }, 1000)
  } catch { ElMessage.error('无法访问麦克风') }
}
function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop()
  isRecording.value = false
  if (recordingTimer) { clearInterval(recordingTimer); recordingTimer = null }
}
function formatTime(sec: number) {
  const m = Math.floor(sec / 60).toString().padStart(2, '0')
  const s = (sec % 60).toString().padStart(2, '0')
  return m + ':' + s
}"""
c = c.replace(old_funcs, "")

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print("2. Doctor MessagesView.vue refactored")

# ── 3. Patient DoctorMessagesView.vue ──
path = os.path.join(BASE, 'src', 'views', 'patient', 'DoctorMessagesView.vue')
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Replace recording refs
old_rec3 = """const imageInput = ref<HTMLInputElement>()
const uploadingMedia = ref(false)
const isRecording = ref(false)
const recordingSeconds = ref(0)
let mediaRecorder: MediaRecorder | null = null
let recordedChunks: Blob[] = []
let recordingTimer: ReturnType<typeof setInterval> | null = null"""

new_rec3 = """const imageInput = ref<HTMLInputElement>()
const uploadingMedia = ref(false)
const voiceRecorder = useVoiceRecorder(async (blob) => {
  const file = new File([blob], 'recording.webm', { type: 'audio/webm' })
  uploadingMedia.value = true
  try {
    const res = await doctorService.uploadVoice(file)
    if (res.data.success) await sendMessage('voice', res.data.url)
  } catch { ElMessage.error('语音上传失败') }
  finally { uploadingMedia.value = false }
})
const { isRecording, recordingSeconds, toggleRecording, stopRecording, formatTime } = voiceRecorder"""
c = c.replace(old_rec3, new_rec3)

# Add import
c = c.replace(
    "import { ChatDotRound, Picture, Microphone, VideoPause } from '@element-plus/icons-vue'",
    "import { ChatDotRound, Picture, Microphone, VideoPause } from '@element-plus/icons-vue'\nimport { useVoiceRecorder } from '@/composables/useVoiceRecorder'\nimport { useMediaUrl } from '@/composables/useMediaUrl'"
)

# Replace apiBase + mediaSrc
old_media3 = """const auth = useAuthStore()
const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function mediaSrc(url: string) {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return apiBase + url
}"""
c = c.replace(old_media3, "const auth = useAuthStore()\nconst { mediaSrc } = useMediaUrl()")

# Remove old recording functions
c = c.replace(old_funcs, "")

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print("3. Patient DoctorMessagesView.vue refactored")

print("\nAll done!")
