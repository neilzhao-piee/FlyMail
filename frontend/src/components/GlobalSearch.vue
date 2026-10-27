<template>
  <button class="gs-trigger" type="button" :title='$t("全局搜索（Ctrl/⌘ + K）")' @click="openPanel">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  </button>

  <Teleport to="body">
    <div v-if="open" class="gs-overlay" @click.self="closePanel">
      <div class="gs-panel">
        <div class="gs-search-row">
          <svg class="gs-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref="inputEl"
            v-model="keyword"
            class="gs-input"
            type="search"
            :placeholder='$t("搜索所有邮箱（主题 / 发件人 / 正文；中文 ≥3 字走全文索引）")'
            @keydown.enter.prevent="doSearch"
            @keydown.esc.prevent="closePanel"
          />
          <select v-model="sort" class="gs-sort" :title='$t("排序方式")' @change="doSearch">
            <option value="date">{{ $t("按时间") }}</option>
            <option value="relevance">{{ $t("按相关度") }}</option>
          </select>
          <button class="gs-btn" type="button" :disabled="loading || !keyword.trim()" @click="doSearch">
            {{ loading ? '搜索中…' : '搜索' }}
          </button>
        </div>

        <div v-if="error" class="gs-error">{{ error }}</div>

        <div v-if="result" class="gs-meta">{{ $t("共") }}{{ result.total }}{{ $t("条 ·") }}{{ result.took_ms }} ms · {{ result.mode === 'fts' ? '全文索引' : '模糊匹配（短词/索引不可用）' }}
        </div>

        <div class="gs-list">
          <button
            v-for="item in result?.messages || []"
            :key="item.account_id + ':' + item.folder + ':' + item.uid"
            class="gs-item"
            type="button"
            @click="pick(item)"
          >
            <div class="gs-item-head">
              <span class="gs-account">{{ item.account_email || item.account_id }}</span>
              <span class="gs-folder">{{ item.folder }}</span>
              <span v-if="item.has_attachments" class="gs-attach" :title='$t("含附件")'>📎</span>
              <span class="gs-date">{{ formatDate(item.date) }}</span>
            </div>
            <div class="gs-subject" v-html="renderSnippet(item)"></div>
            <div class="gs-from">{{ item.from_addr }}</div>
          </button>
        </div>

        <div v-if="!loading && result && result.messages.length === 0" class="gs-empty">{{ $t("没有匹配的邮件") }}</div>
        <div v-if="!result && !loading && !error" class="gs-empty">{{ $t("输入关键词后回车；结果覆盖所有已同步的邮箱与文件夹") }}</div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import { nextTick, onMounted, onUnmounted, ref } from 'vue';
import api from '../utils/api';

const emit = defineEmits<{
  (e: 'open', payload: { account_id: string; folder: string; uid: number; id: string }): void;
}>();

const open = ref(false);
const keyword = ref('');
const sort = ref<'date' | 'relevance'>('date');
const loading = ref(false);
const error = ref('');
const result = ref<{
  messages: any[];
  total: number;
  page: number;
  page_size: number;
  query: string;
  mode: string;
  took_ms: number;
} | null>(null);
const inputEl = ref<HTMLInputElement | null>(null);

function openPanel() {
  open.value = true;
  nextTick(() => inputEl.value?.focus());
}

function closePanel() {
  open.value = false;
}

async function doSearch() {
  const q = keyword.value.trim();
  if (!q || loading.value) return;
  loading.value = true;
  error.value = '';
  try {
    result.value = await api.get('/search', {
      params: { q, page: 1, page_size: 50, sort: sort.value },
    });
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || t("搜索失败");
    result.value = null;
  } finally {
    loading.value = false;
  }
}

function pick(item: any) {
  emit('open', {
    account_id: item.account_id,
    folder: item.folder,
    uid: Number(item.uid),
    id: String(item.id),
  });
  closePanel();
}

function escapeHtml(text: string): string {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** snippet 里只有 <mark> 是高亮标记，其余内容一律转义，避免邮件正文里的 HTML 被执行 */
function renderSnippet(item: any): string {
  const raw = String(item?.snippet || item?.subject || '');
  return escapeHtml(raw)
    .replace(/&lt;mark&gt;/g, '<mark>')
    .replace(/&lt;\/mark&gt;/g, '</mark>');
}

function formatDate(value: string): string {
  if (!value) return '';
  const text = String(value);
  const m = text.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[1]}-${m[2]}-${m[3]}` : text.slice(0, 16);
}

function onGlobalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    openPanel();
  }
}

onMounted(() => window.addEventListener('keydown', onGlobalKeydown));
onUnmounted(() => window.removeEventListener('keydown', onGlobalKeydown));
</script>

<style scoped>
.gs-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  opacity: 0.75;
}
.gs-trigger:hover {
  opacity: 1;
  background: rgba(127, 127, 127, 0.12);
}
.gs-trigger svg {
  width: 19px;
  height: 19px;
}

.gs-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(0, 0, 0, 0.42);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 10vh 16px 16px;
}
.gs-panel {
  width: min(760px, 100%);
  max-height: 74vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-1, #fff);
  color: var(--text-1, #1f2328);
  border-radius: 14px;
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.28);
  overflow: hidden;
}
.gs-search-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(127, 127, 127, 0.18);
}
.gs-search-icon {
  width: 18px;
  height: 18px;
  opacity: 0.6;
  flex: none;
}
.gs-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: inherit;
  font-size: 15px;
}
.gs-sort {
  border: 1px solid rgba(127, 127, 127, 0.25);
  border-radius: 8px;
  padding: 4px 6px;
  background: transparent;
  color: inherit;
  font-size: 13px;
}
.gs-btn {
  border: none;
  border-radius: 8px;
  padding: 7px 14px;
  background: #3d7eff;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.gs-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.gs-meta,
.gs-error,
.gs-empty {
  padding: 8px 14px;
  font-size: 12px;
  opacity: 0.72;
}
.gs-error {
  color: #d33;
  opacity: 1;
}
.gs-list {
  overflow-y: auto;
  padding: 4px 6px 10px;
}
.gs-item {
  display: block;
  width: 100%;
  text-align: left;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: inherit;
  padding: 9px 10px;
  cursor: pointer;
}
.gs-item:hover {
  background: rgba(127, 127, 127, 0.12);
}
.gs-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  opacity: 0.7;
  margin-bottom: 3px;
}
.gs-account {
  font-weight: 600;
  opacity: 0.95;
}
.gs-folder {
  border-radius: 6px;
  padding: 0 6px;
  background: rgba(127, 127, 127, 0.14);
}
.gs-date {
  margin-left: auto;
}
.gs-subject {
  font-size: 14px;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.gs-subject :deep(mark) {
  background: #ffe58f;
  color: inherit;
  border-radius: 3px;
  padding: 0 1px;
}
.gs-from {
  margin-top: 3px;
  font-size: 12px;
  opacity: 0.68;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
