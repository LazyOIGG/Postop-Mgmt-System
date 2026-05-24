import os

# ── Doctor MessagesView.vue ──
path = os.path.join(os.path.dirname(__file__), '..', '..', '前端', 'postop-mgmt-frontend', 'src', 'views', 'doctor', 'MessagesView.vue')
path = os.path.normpath(path)
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add icon imports
content = content.replace(
    "import { useRoute } from 'vue-router'",
    "import { useRoute } from 'vue-router'\nimport { Picture, Microphone, VideoPause } from '@element-plus/icons-vue'"
)

# Add refs
content = content.replace(
    "const sendingMsg = ref(false)",
    "const sendingMsg = ref(false)\nconst imageInput = ref<HTMLInputElement>()\nconst uploadingMedia = ref(false)\nconst isRecording = ref(false)\nconst recordingSeconds = ref(0)\nlet mediaRecorder: MediaRecorder | null = null\nlet recordedChunks: Blob[] = []\nlet recordingTimer: ReturnType<typeof setInterval> | null = null"
)

# Replace sendMessage function
old_send = """async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || !selectedPatient.value || sendingMsg.value) return

  sendingMsg.value = true
  try {
    await doctorService.sendMessage(selectedPatient.value, text)
    inputText.value = ''
    await loadMessages()
  } catch {
    ElMessage.error("发送消息失败")
  } finally {
    sendingMsg.value = false
  }
}"""

new_send = """async function sendMessage(messageType = 'text', mediaUrl?: string) {
  const text = inputText.value.trim()
  if (!text && messageType === 'text') return
  if (!selectedPatient.value || sendingMsg.value) return

  sendingMsg.value = true
  try {
    await doctorService.sendMessage(selectedPatient.value, text || '[图片]', messageType, mediaUrl)
    inputText.value = ''
    await loadMessages()
  } catch {
    ElMessage.error("发送消息失败")
  } finally {
    sendingMsg.value = false
  }
}

async function sendImage() { imageInput.value?.click() }
async function onImageSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = ''
  uploadingMedia.value = true
  try {
    const res = await doctorService.uploadImage(file)
    if (res.data.success) await sendMessage('image', res.data.url)
  } catch { ElMessage.error("图片上传失败") }
  finally { uploadingMedia.value = false }
}

async function toggleRecording() {
  if (isRecording.value) stopRecording()
  else await startRecording()
}
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    recordedChunks = []
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data) }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(recordedChunks, { type: 'audio/webm' })
      const file = new File([blob], 'recording.webm', { type: 'audio/webm' })
      uploadingMedia.value = true
      try {
        const res = await doctorService.uploadVoice(file)
        if (res.data.success) await sendMessage('voice', res.data.url)
      } catch { ElMessage.error("语音上传失败") }
      finally { uploadingMedia.value = false }
    }
    mediaRecorder.start()
    isRecording.value = true
    recordingSeconds.value = 0
    recordingTimer = setInterval(() => { recordingSeconds.value++; if (recordingSeconds.value >= 60) stopRecording() }, 1000)
  } catch { ElMessage.error("无法访问麦克风") }
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

content = content.replace(old_send, new_send)

# Update message bubble template
old_bubble = """              <div class="msg-content">{{ m.content }}</div>
                <div class="msg-time">{{ m.created_at?.slice(0, 16) }}</div>"""

new_bubble = """              <img v-if="(m as any).message_type === 'image' && (m as any).media_url" :src="(m as any).media_url" class="msg-image" />
              <div v-if="(m as any).message_type === 'voice' && (m as any).media_url" class="msg-voice">
                <audio :src="(m as any).media_url" controls style="height:32px;max-width:200px" />
              </div>
              <div class="msg-content" v-if="(m as any).message_type !== 'image'">{{ m.content }}</div>
              <div class="msg-time">{{ m.created_at?.slice(0, 16) }}</div>"""

content = content.replace(old_bubble, new_bubble)

# Update chat input area
old_input = """          <div class="chat-input-area">
            <el-input
              v-model="inputText"
              placeholder="输入消息..."
              size="large"
              @keyup.enter="sendMessage"
            >"""

new_input = """          <div class="chat-input-area">
            <input ref="imageInput" type="file" accept="image/*" style="display:none" @change="onImageSelected" />
            <div class="input-row">
              <el-button circle :disabled="sendingMsg || uploadingMedia" @click="sendImage" class="input-action-btn">
                <el-icon :size="18"><Picture /></el-icon>
              </el-button>
              <el-button circle :type="isRecording ? 'danger' : 'default'" :disabled="sendingMsg && !isRecording" @click="toggleRecording" class="input-action-btn" :class="{ recording: isRecording }">
                <el-icon v-if="!isRecording" :size="18"><Microphone /></el-icon>
                <el-icon v-else :size="18"><VideoPause /></el-icon>
              </el-button>
            <el-input
              v-model="inputText"
              :placeholder="isRecording ? '录音中 '+formatTime(recordingSeconds)+'...' : '输入消息...'"
              size="large"
              :disabled="isRecording"
              @keyup.enter="sendMessage('text')"
            >"""

content = content.replace(old_input, new_input)

# Close input-row div
old_close = """              </template>
            </el-input>
          </div>
        </template>
      </div>
    </div>"""

new_close = """              </template>
            </el-input>
            </div>
            <div v-if="isRecording" class="recording-bar">
              <div class="recording-pulse"></div>
              <span>录音中 {{ formatTime(recordingSeconds) }}</span>
            </div>
          </div>
        </template>
      </div>
    </div>"""

content = content.replace(old_close, new_close)

# Add CSS
content = content.replace(
    "</style>",
    """
.msg-image { max-width: 200px; max-height: 160px; border-radius: 12px; display: block; margin-bottom: 4px; }
.msg-voice { margin-bottom: 4px; }
.input-row { display: flex; align-items: center; gap: 8px; }
.input-action-btn { flex-shrink: 0; width: 40px; height: 40px; border-color: var(--color-border); transition: all 0.3s ease; }
.input-action-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.input-action-btn.recording { animation: recPulse 1s ease-in-out infinite; }
.recording-bar { display: flex; align-items: center; gap: 8px; padding: 6px 12px; margin-top: 6px; background: var(--color-danger-bg); border-radius: var(--radius-sm); font-size: 12px; color: var(--color-danger); }
.recording-pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--color-danger); animation: blink 1s infinite; }
@keyframes recPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(198,107,61,0.4); } 50% { box-shadow: 0 0 0 8px rgba(198,107,61,0); } }
@keyframes blink { 0%,100% { opacity: 0.2; } 50% { opacity: 0.8; } }
</style>"""
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Doctor MessagesView.vue updated, length:", len(content))

# ── Patient DoctorMessagesView.vue ──
path2 = os.path.join(os.path.dirname(__file__), '..', '..', '前端', 'postop-mgmt-frontend', 'src', 'views', 'patient', 'DoctorMessagesView.vue')
path2 = os.path.normpath(path2)
with open(path2, 'r', encoding='utf-8') as f:
    content2 = f.read()

# Add icon imports
content2 = content2.replace(
    "import { ChatDotRound } from '@element-plus/icons-vue'",
    "import { ChatDotRound, Picture, Microphone, VideoPause } from '@element-plus/icons-vue'"
)

# Add refs
content2 = content2.replace(
    "const sending = ref(false)",
    "const sending = ref(false)\nconst imageInput = ref<HTMLInputElement>()\nconst uploadingMedia = ref(false)\nconst isRecording = ref(false)\nconst recordingSeconds = ref(0)\nlet mediaRecorder: MediaRecorder | null = null\nlet recordedChunks: Blob[] = []\nlet recordingTimer: ReturnType<typeof setInterval> | null = null"
)

# Replace sendMessage
old_send2 = """async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || !username || sending.value) return

  sending.value = true
  try {
    await doctorService.sendMessageFromPatient(username, text)
    inputText.value = ''
    await fetchMessages()
    scrollToBottom()
  } catch {
    ElMessage.error("发送消息失败")
  } finally {
    sending.value = false
  }
}"""

new_send2 = """async function sendMessage(messageType = 'text', mediaUrl?: string) {
  const text = inputText.value.trim()
  if (!text && messageType === 'text') return
  if (!username || sending.value) return

  sending.value = true
  try {
    await doctorService.sendMessageFromPatient(username, text || '[图片]', messageType, mediaUrl)
    inputText.value = ''
    await fetchMessages()
    scrollToBottom()
  } catch {
    ElMessage.error("发送消息失败")
  } finally {
    sending.value = false
  }
}

async function sendImage() { imageInput.value?.click() }
async function onImageSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = ''
  uploadingMedia.value = true
  try {
    const res = await doctorService.uploadImage(file)
    if (res.data.success) await sendMessage('image', res.data.url)
  } catch { ElMessage.error("图片上传失败") }
  finally { uploadingMedia.value = false }
}

async function toggleRecording() {
  if (isRecording.value) stopRecording()
  else await startRecording()
}
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    recordedChunks = []
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data) }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(recordedChunks, { type: 'audio/webm' })
      const file = new File([blob], 'recording.webm', { type: 'audio/webm' })
      uploadingMedia.value = true
      try {
        const res = await doctorService.uploadVoice(file)
        if (res.data.success) await sendMessage('voice', res.data.url)
      } catch { ElMessage.error("语音上传失败") }
      finally { uploadingMedia.value = false }
    }
    mediaRecorder.start()
    isRecording.value = true
    recordingSeconds.value = 0
    recordingTimer = setInterval(() => { recordingSeconds.value++; if (recordingSeconds.value >= 60) stopRecording() }, 1000)
  } catch { ElMessage.error("无法访问麦克风") }
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

content2 = content2.replace(old_send2, new_send2)

# Update bubble template
old_bubble2 = """        <div class="msg-content">{{ m.content }}</div>
        <div class="msg-time">{{ m.created_at?.slice(0, 16) }}</div>"""

new_bubble2 = """        <img v-if="(m as any).message_type === 'image' && (m as any).media_url" :src="(m as any).media_url" class="msg-image" />
        <div v-if="(m as any).message_type === 'voice' && (m as any).media_url" class="msg-voice">
          <audio :src="(m as any).media_url" controls style="height:32px;max-width:200px" />
        </div>
        <div class="msg-content" v-if="(m as any).message_type !== 'image'">{{ m.content }}</div>
        <div class="msg-time">{{ m.created_at?.slice(0, 16) }}</div>"""

content2 = content2.replace(old_bubble2, new_bubble2)

# Update input area
old_input2 = """    <div class="msg-input-area">
      <el-input
        v-model="inputText"
        placeholder="输入消息联系医生..."
        size="large"
        :disabled="sending"
        @keyup.enter="sendMessage"
      >"""

new_input2 = """    <div class="msg-input-area">
      <input ref="imageInput" type="file" accept="image/*" style="display:none" @change="onImageSelected" />
      <div class="input-row">
        <el-button circle :disabled="sending || uploadingMedia" @click="sendImage" class="input-action-btn">
          <el-icon :size="18"><Picture /></el-icon>
        </el-button>
        <el-button circle :type="isRecording ? 'danger' : 'default'" :disabled="sending && !isRecording" @click="toggleRecording" class="input-action-btn" :class="{ recording: isRecording }">
          <el-icon v-if="!isRecording" :size="18"><Microphone /></el-icon>
          <el-icon v-else :size="18"><VideoPause /></el-icon>
        </el-button>
      <el-input
        v-model="inputText"
        :placeholder="isRecording ? '录音中 '+formatTime(recordingSeconds)+'...' : '输入消息联系医生...'"
        size="large"
        :disabled="sending || isRecording"
        @keyup.enter="sendMessage('text')"
      >"""

content2 = content2.replace(old_input2, new_input2)

# Close input row
old_close2 = """        </template>
      </el-input>
    </div>"""

new_close2 = """        </template>
      </el-input>
      </div>
      <div v-if="isRecording" class="recording-bar">
        <div class="recording-pulse"></div>
        <span>录音中 {{ formatTime(recordingSeconds) }}</span>
      </div>
    </div>"""

content2 = content2.replace(old_close2, new_close2)

# Add CSS
content2 = content2.replace(
    "</style>",
    """
.msg-image { max-width: 200px; max-height: 160px; border-radius: 12px; display: block; margin-bottom: 4px; }
.msg-voice { margin-bottom: 4px; }
.input-row { display: flex; align-items: center; gap: 8px; }
.input-action-btn { flex-shrink: 0; width: 40px; height: 40px; border-color: var(--color-border); transition: all 0.3s ease; }
.input-action-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.input-action-btn.recording { animation: recPulse 1s ease-in-out infinite; }
.recording-bar { display: flex; align-items: center; gap: 8px; padding: 6px 12px; margin-top: 6px; background: var(--color-danger-bg); border-radius: var(--radius-sm); font-size: 12px; color: var(--color-danger); }
.recording-pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--color-danger); animation: blink 1s infinite; }
@keyframes recPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(198,107,61,0.4); } 50% { box-shadow: 0 0 0 8px rgba(198,107,61,0); } }
@keyframes blink { 0%,100% { opacity: 0.2; } 50% { opacity: 0.8; } }
</style>"""
)

with open(path2, 'w', encoding='utf-8') as f:
    f.write(content2)
print("Patient DoctorMessagesView.vue updated, length:", len(content2))
