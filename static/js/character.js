/* 角色管理 */

const Character = {
  projectId: null,
  selectedId: null,

  init(projectId) {
    this.projectId = projectId;
    this.selectedId = null;
  },

  async loadList() {
    try {
      const data = await API.get(`/projects/${this.projectId}/characters`);
      this.renderList(data.characters);
    } catch (e) {
      console.error('加载角色失败:', e);
    }
  },

  renderList(chars) {
    const el = document.getElementById('char-list');
    if (!chars || !chars.length) {
      el.innerHTML = '<div class="no-data">暂无角色<br><small>结构化后会自动识别</small></div>';
      return;
    }

    el.innerHTML = chars.map(c => `
      <div class="char-item ${this.selectedId === c.id ? 'active' : ''} ${c.is_narrator ? 'narrator-item' : ''}"
           onclick="Character.select('${c.id}')">
        <div class="char-name">${this.escapeHtml(c.name)}${c.is_narrator ? ' <small style="color:var(--text2)">(系统)</small>' : ''}</div>
        <div class="char-meta">
          ${c.gender || ''} ${c.age ? '· ' + c.age : ''} ${c.role ? '· ' + c.role : ''}
        </div>
      </div>
    `).join('');
  },

  select(id) {
    this.selectedId = id;
    this.renderDetail(id);
    this.loadList(); // 刷新高亮
  },

  async renderDetail(id) {
    const el = document.getElementById('char-detail');
    const data = await API.get(`/projects/${this.projectId}/characters`);

    const char = data.characters.find(c => c.id === id);
    if (!char) {
      el.style.display = 'none';
      return;
    }

    const isNarrator = !!char.is_narrator;

    el.style.display = 'block';
    el.innerHTML = `
      <div style="margin-bottom:12px">
        <strong style="font-size:16px;color:var(--accent2)">${this.escapeHtml(char.name)}</strong>
        ${isNarrator ? '<span style="font-size:11px;color:var(--text2);margin-left:8px">系统内置</span>' : ''}
      </div>
      ${!isNarrator ? `
      <div class="field">
        <label>性别</label>
        <input value="${char.gender || ''}" onchange="Character.updateField('${id}', 'gender', this.value)">
      </div>
      <div class="field">
        <label>年龄</label>
        <input value="${char.age || ''}" onchange="Character.updateField('${id}', 'age', this.value)">
      </div>
      <div class="field">
        <label>性格</label>
        <input value="${char.personality || ''}" onchange="Character.updateField('${id}', 'personality', this.value)">
      </div>
      <div class="field">
        <label>角色定位</label>
        <input value="${char.role || ''}" onchange="Character.updateField('${id}', 'role', this.value)">
      </div>
      ` : `
      <div class="field">
        <label>性别</label>
        <input value="${char.gender || ''}" onchange="Character.updateField('${id}', 'gender', this.value)">
      </div>
      <div class="field">
        <label>年龄</label>
        <input value="${char.age || ''}" onchange="Character.updateField('${id}', 'age', this.value)">
      </div>
      <div class="field">
        <label>性格</label>
        <input value="${char.personality || ''}" onchange="Character.updateField('${id}', 'personality', this.value)">
      </div>
      <div class="field">
        <label>角色定位</label>
        <input value="${char.role || ''}" onchange="Character.updateField('${id}', 'role', this.value)">
      </div>
      `}
      <div class="field">
        <label>音色描述</label>
        <textarea onchange="Character.updateField('${id}', 'voice_description', this.value)">${char.voice_description || ''}</textarea>
      </div>
      <div class="field">
        <label>声音 Prompt</label>
        <textarea onchange="Character.updateVoiceField('${id}', 'prompt', this.value)">${char.voice?.prompt || ''}</textarea>
      </div>
      <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
        <button class="btn btn-primary btn-sm" onclick="VoiceDesign.open('${id}')">🎨 声音设计</button>
        ${char.voice?.sample_audio ? `<button class="btn btn-sm" onclick="Character.playSample('${id}')">🔊 试听</button>` : ''}
        <label class="btn btn-sm" style="cursor:pointer;margin:0">
          📁 上传音色
          <input type="file" accept="audio/*" style="display:none"
                 onchange="Character.uploadAudio('${id}', this)">
        </label>
        ${char.voice?.reference_audio ? `<button class="btn btn-sm" onclick="Character.playUploaded('${id}')">🔊 试听上传</button><span style="font-size:11px;color:var(--accent);align-self:center">✅ 已上传</span>` : ''}
        <button class="btn btn-sm" onclick="Character.save('${id}')">💾 保存</button>
        ${!isNarrator ? `<button class="btn btn-sm" style="color:var(--danger)" onclick="Character.deleteChar('${id}')">🗑 删除</button>` : ''}
      </div>
      ${char.voice?.sample_audio ? `<audio id="audio-${id}" src="/output/${char.voice.sample_audio}?_=${Date.now()}" style="display:none"></audio>` : ''}
      ${char.voice?.reference_audio ? `<audio id="audio-upload-${id}" src="/output/${this.projectId}/upload_${id}.wav" style="display:none"></audio>` : ''}
    `;
  },

  async updateField(id, field, value) {
    try {
      await API.put(`/projects/${this.projectId}/characters/${id}`, { [field]: value });
    } catch (e) {
      console.error('更新角色失败:', e);
    }
  },

  async updateVoiceField(id, field, value) {
    try {
      await API.put(`/projects/${this.projectId}/characters/${id}`, {
        voice: { [field]: value },
      });
    } catch (e) {
      console.error('更新角色声音失败:', e);
    }
  },

  async save(id) {
    App.toast('角色已保存', 'success');
  },

  /* ========== 手动添加角色 ========== */

  showAddDialog() {
    const name = prompt('请输入角色名称：');
    if (!name || !name.trim()) return;

    const trimmed = name.trim();

    // 检查是否已存在同名角色
    API.get(`/projects/${this.projectId}/characters`).then(data => {
      const exists = data.characters.some(c => c.name === trimmed);
      if (exists) {
        App.toast(`角色"${trimmed}"已存在`, 'error');
        return;
      }
      this.addCharacter(trimmed);
    }).catch(() => {
      // 查询失败直接尝试添加
      this.addCharacter(trimmed);
    });
  },

  async addCharacter(name) {
    try {
      const result = await API.post(`/projects/${this.projectId}/characters`, {
        name: name,
        gender: '',
        age: '',
        personality: '',
        role: '',
        voice_description: '',
      });
      App.toast(`角色"${name}"已添加`, 'success');
      await this.loadList();
      // 自动选中新添加的角色
      this.select(result.id);
    } catch (e) {
      App.toast('添加角色失败: ' + (e.message || '未知错误'), 'error');
    }
  },

  async deleteChar(id) {
    // 找到角色名用于确认
    const data = await API.get(`/projects/${this.projectId}/characters`);
    const char = data.characters.find(c => c.id === id);
    const name = char ? char.name : id;
    if (!confirm(`确定要删除角色"${name}"吗？此操作不可撤销。`)) return;

    try {
      await API.del(`/projects/${this.projectId}/characters/${id}`);
      App.toast(`角色"${name}"已删除`, 'success');
      this.selectedId = null;
      document.getElementById('char-detail').style.display = 'none';
      await this.loadList();
    } catch (e) {
      App.toast('删除失败: ' + (e.message || '未知错误'), 'error');
    }
  },

  playSample(id) {
    const audio = document.getElementById(`audio-${id}`);
    if (audio) audio.play();
  },

  playUploaded(id) {
    const audio = document.getElementById(`audio-upload-${id}`);
    if (audio) audio.play().catch(() => App.toast('播放失败，文件可能不存在', 'error'));
  },

  async uploadAudio(charId, inputEl) {
    const file = inputEl.files[0];
    if (!file) return;

    // 大小限制 20MB
    if (file.size > 20 * 1024 * 1024) {
      App.toast('文件过大，请选择 20MB 以内的音频文件', 'error');
      inputEl.value = '';
      return;
    }

    App.toast('正在上传并转换...', 'success');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const resp = await fetch(
        `/api/v1/projects/${this.projectId}/characters/${charId}/upload-audio`,
        { method: 'POST', body: formData }
      );

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: '上传失败' }));
        throw new Error(err.detail);
      }

      const data = await resp.json();
      const msg = data.converted_to_wav
        ? `音色已上传并转为 WAV: ${data.filename}`
        : `音色已上传: ${data.filename}`;
      App.toast(msg, 'success');

      // 刷新详情以显示"✅ 已上传"状态
      this.renderDetail(charId);
    } catch (e) {
      App.toast('上传失败: ' + (e.message || '未知错误'), 'error');
    } finally {
      inputEl.value = '';
    }
  },

  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },
};
