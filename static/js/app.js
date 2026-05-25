/* AI声工坊 主应用逻辑 */

const App = {
  currentProjectId: null,

  /* ========== 项目操作 ========== */

  newProject() {
    // 显示新建项目对话框
    document.getElementById('np-txt-file').value = '';
    document.getElementById('np-output-dir').value = '';
    document.getElementById('np-folder-browser').style.display = 'none';
    document.getElementById('new-project-modal').classList.add('show');
  },

  async browseFolder() {
    // 优先使用原生 Windows 文件夹选择对话框
    try {
      const resp = await fetch('/api/v1/pick-folder');
      const data = await resp.json();
      if (data.path) {
        document.getElementById('np-output-dir').value = data.path;
        return;
      }
    } catch (e) {
      console.warn('原生文件夹选择失败，使用内置浏览器:', e);
    }
    // 降级：内置文件夹浏览器
    this._browsePath = '';
    await this._loadFolderEntries('');
  },

  async _loadFolderEntries(path) {
    this._browsePath = path;
    const browser = document.getElementById('np-folder-browser');
    browser.style.display = 'block';
    document.getElementById('np-browse-path').textContent = '当前位置: ' + (path || '驱动器列表');

    try {
      const resp = await fetch(`/api/v1/browse?path=${encodeURIComponent(path)}`);
      const data = await resp.json();
      const list = document.getElementById('np-folder-list');
      if (data.entries.length === 0) {
        list.innerHTML = '<div style="padding:8px;color:var(--text2);font-size:11px">此目录下无子文件夹</div>';
      } else {
        list.innerHTML = data.entries.map(e => `
          <div style="padding:5px 8px;cursor:pointer;font-size:12px;border-bottom:1px solid var(--border)"
               ondblclick="App._loadFolderEntries('${this.escapeHtml(e.path).replace(/'/g, "\\'")}')"
               onclick="App._selectBrowsePath('${this.escapeHtml(e.path).replace(/'/g, "\\'")}')">
            📁 ${this.escapeHtml(e.name)}
          </div>
        `).join('');
      }
      this._browseParent = data.parent || '';
    } catch (e) {
      document.getElementById('np-folder-list').innerHTML = '<div style="padding:8px;color:var(--danger)">加载失败</div>';
    }
  },

  _selectBrowsePath(path) {
    this._browsePath = path;
    document.getElementById('np-browse-path').textContent = '当前位置: ' + path;
    document.getElementById('np-folder-list').querySelectorAll('div').forEach(d => d.style.background = '');
  },

  browseParent() {
    if (this._browseParent !== undefined && this._browseParent !== '') {
      this._loadFolderEntries(this._browseParent);
    }
  },

  selectFolder() {
    document.getElementById('np-output-dir').value = this._browsePath;
    document.getElementById('np-folder-browser').style.display = 'none';
  },

  async confirmNewProject() {
    const fileInput = document.getElementById('np-txt-file');
    const file = fileInput.files[0];
    if (!file) {
      this.toast('请选择 TXT 文件', 'error');
      return;
    }

    const outputDir = document.getElementById('np-output-dir').value.trim();

    try {
      this.setStatus('解析 TXT...');
      const formData = new FormData();
      formData.append('file', file);
      if (outputDir) {
        formData.append('output_dir', outputDir);
      }

      const resp = await fetch('/api/v1/projects', { method: 'POST', body: formData });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: '创建失败' }));
        throw new Error(err.detail);
      }
      const data = await resp.json();

      document.getElementById('new-project-modal').classList.remove('show');
      this.openWorkspace(data.project);
      this.toast(`项目创建成功！共 ${data.chapter_count} 章`, 'success');
    } catch (e) {
      this.toast('创建失败: ' + e.message, 'error');
    }
  },

  openProject() {
    document.getElementById('file-awb').click();
  },

  async handleOpenProject(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
      this.setStatus('加载项目...');
      const data = await API.upload('/projects/open', file);
      this.openWorkspace(data.project);
      this.toast(`项目打开成功！共 ${data.chapter_count} 章`, 'success');
    } catch (e) {
      this.toast('打开失败: ' + e.message, 'error');
    }
    event.target.value = '';
  },

  openWorkspace(project) {
    this.currentProjectId = project.id;

    // 切换 UI
    document.getElementById('welcome-page').style.display = 'none';
    document.getElementById('workspace').style.display = 'flex';
    document.getElementById('topbar-actions').style.display = 'none';
    document.getElementById('topbar-project').style.display = 'flex';

    document.getElementById('status-project').textContent = project.title;

    // 初始化子模块
    Chapter.init(project.id);
    Character.init(project.id);

    // 加载数据
    Chapter.loadList();
    Character.loadList();

    this.setStatus('就绪');
    this.updateStatus();
  },

  async refresh() {
    if (!this.currentProjectId) return;
    try {
      const data = await API.get(`/projects/${this.currentProjectId}`);
      Character.loadList();
    } catch (e) {
      console.error('刷新失败:', e);
    }
  },

  /* ========== 文字替换 ========== */

  async showReplaceModal() {
    if (!this.currentProjectId) {
      this.toast('请先打开项目', 'error');
      return;
    }

    let rules = [];
    try {
      const data = await API.get(`/projects/${this.currentProjectId}/text-replacements`);
      rules = data.replacements || [];
    } catch (e) {
      console.error('加载替换规则失败:', e);
    }

    const el = document.getElementById('replace-rules');
    el.innerHTML = rules.map((r, i) => `
      <div class="replace-row" style="display:flex;gap:8px;margin-bottom:6px;align-items:center">
        <input value="${this.escapeHtml(r.from || '')}" placeholder="查找文本"
               onchange="App.updateReplaceRule(${i}, 'from', this.value)"
               style="flex:1">
        <span style="color:var(--text2)">→</span>
        <input value="${this.escapeHtml(r.to || '')}" placeholder="替换文本"
               onchange="App.updateReplaceRule(${i}, 'to', this.value)"
               style="flex:1">
        <button class="btn btn-sm" style="color:var(--danger);padding:2px 6px"
                onclick="App.removeReplaceRule(${i})">✕</button>
      </div>
    `).join('');

    this._replaceRules = JSON.parse(JSON.stringify(rules));
    document.getElementById('replace-modal').classList.add('show');
  },

  addReplaceRule() {
    const rule = { from: '', to: '' };
    this._replaceRules.push(rule);
    this._renderReplaceRules();
  },

  updateReplaceRule(idx, field, value) {
    if (idx >= 0 && idx < this._replaceRules.length) {
      this._replaceRules[idx][field] = value;
    }
  },

  removeReplaceRule(idx) {
    this._replaceRules.splice(idx, 1);
    this._renderReplaceRules();
  },

  _renderReplaceRules() {
    const el = document.getElementById('replace-rules');
    el.innerHTML = this._replaceRules.map((r, i) => `
      <div class="replace-row" style="display:flex;gap:8px;margin-bottom:6px;align-items:center">
        <input value="${this.escapeHtml(r.from || '')}" placeholder="查找文本"
               onchange="App.updateReplaceRule(${i}, 'from', this.value)"
               style="flex:1">
        <span style="color:var(--text2)">→</span>
        <input value="${this.escapeHtml(r.to || '')}" placeholder="替换文本"
               onchange="App.updateReplaceRule(${i}, 'to', this.value)"
               style="flex:1">
        <button class="btn btn-sm" style="color:var(--danger);padding:2px 6px"
                onclick="App.removeReplaceRule(${i})">✕</button>
      </div>
    `).join('');
  },

  async saveReplacements() {
    if (!this.currentProjectId) return;
    const valid = this._replaceRules.filter(r => r.from && r.from !== r.to);
    try {
      await API.put(`/projects/${this.currentProjectId}/text-replacements`, {
        replacements: valid,
      });
      this.toast(`已保存 ${valid.length} 条替换规则`, 'success');
      document.getElementById('replace-modal').classList.remove('show');
    } catch (e) {
      this.toast('保存失败: ' + e.message, 'error');
    }
  },

  async saveProject() {
    if (!this.currentProjectId) return;
    try {
      this.setStatus('保存中...');
      const resp = await fetch(`/api/v1/projects/${this.currentProjectId}/save`, { method: 'POST' });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: '保存失败' }));
        throw new Error(err.detail);
      }

      // 获取文件名
      const disposition = resp.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename="(.+)"/);
      const filename = match ? match[1] : 'project.awb';

      const blob = await resp.blob();

      // 优先使用原生"另存为"对话框 (File System Access API)
      if (window.showSaveFilePicker) {
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: filename,
            types: [{
              description: 'AI声工坊项目文件',
              accept: { 'application/json': ['.awb'] },
            }],
          });
          const writable = await handle.createWritable();
          await writable.write(blob);
          await writable.close();
          this.toast('项目已保存', 'success');
          this.setStatus('就绪');
          return;
        } catch (e) {
          // 用户取消对话框 → 静默返回
          if (e.name === 'AbortError' || e.name === 'DOMException') {
            this.setStatus('就绪');
            return;
          }
          // 其他错误 → 降级到下载方式
          console.warn('showSaveFilePicker 失败，降级到下载:', e);
        }
      }

      // 降级方案：浏览器下载
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      this.toast('项目已保存', 'success');
      this.setStatus('就绪');
    } catch (e) {
      this.toast('保存失败: ' + e.message, 'error');
    }
  },

  async exportProject() {
    if (!this.currentProjectId) return;
    try {
      this.toast('正在导出...', 'success');
      // 导出为文件下载
      const resp = await fetch(`/api/v1/projects/${this.currentProjectId}/export`);
      if (!resp.ok) throw new Error('导出失败');

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'audiobook.zip';
      a.click();
      URL.revokeObjectURL(url);

      this.toast('导出完成！', 'success');
    } catch (e) {
      this.toast('导出失败: ' + e.message, 'error');
    }
  },

  /* ========== 配置 ========== */

  showConfig() {
    Config.load();
    document.getElementById('config-modal').classList.add('show');
  },

  hideConfig() {
    document.getElementById('config-modal').classList.remove('show');
  },

  /* ========== 状态栏 ========== */

  setStatus(msg) {
    document.getElementById('status-msg').textContent = msg;
  },

  async updateStatus() {
    try {
      const data = await API.get('/config');
      const llmProvider = data.llm?.provider || '未配置';
      const ttsProvider = data.tts?.provider || '未配置';
      document.getElementById('status-llm').textContent = `LLM: ${llmProvider}`;
      document.getElementById('status-tts').textContent = `TTS: ${ttsProvider}`;
    } catch (e) {
      // 忽略
    }
  },

  /* ========== Toast ========== */

  toast(msg, type = 'success') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = `toast ${type} show`;
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      el.classList.remove('show');
    }, 3000);
  },

  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  },

  /* ========== 初始化 ========== */

  init() {
    this.updateStatus();

    // 点击弹窗遮罩关闭
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.remove('show');
      });
    });

    // 退出/关闭时自动保存
    window.addEventListener('beforeunload', () => {
      if (App.currentProjectId) {
        navigator.sendBeacon(
          `/api/v1/projects/${App.currentProjectId}/autosave`,
          new Blob([], { type: 'application/json' })
        );
      }
    });
  },
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => App.init());
