/* 章节管理 */

const Chapter = {
  projectId: null,
  currentIdx: null,
  selectedSegIdx: null,
  _cachedChapter: null,   // 当前章节数据缓存
  _audioPlayer: null,    // HTML5 Audio 元素（惰性创建）
  _generatingSeg: null,  // 当前正在生成的 segment idx
  _playbackRate: 1.0,     // 播放速度倍率 (0.5~1.5)

  init(projectId) {
    this.projectId = projectId;
    this.currentIdx = null;
    this.selectedSegIdx = null;
    this._cachedChapter = null;
    this._audioPlayer = null;
    this._generatingSeg = null;
    this.loadSpeed();
  },

  async loadList() {
    try {
      const data = await API.get(`/projects/${this.projectId}/chapters`);
      this.renderList(data.chapters);
    } catch (e) {
      App.toast('加载章节失败: ' + e.message, 'error');
    }
  },

  renderList(chapters) {
    const el = document.getElementById('chapter-list');
    if (!chapters.length) {
      el.innerHTML = '<div class="no-data">暂无章节</div>';
      return;
    }

    el.innerHTML = chapters.map(c => {
      let dotClass = 'raw';
      if (c.status === 'synthesized' && c.synthesized_count === c.segment_count && c.segment_count > 0) {
        dotClass = 'synthesized';
      } else if (c.status === 'structured' || c.segment_count > 0) {
        dotClass = 'structured';
      }

      return `
        <div class="chapter-item ${this.currentIdx === c.index ? 'active' : ''}"
             onclick="Chapter.select(${c.index})">
          <span class="status-dot ${dotClass}"></span>
          <span>${this.escapeHtml(c.title)}</span>
          ${c.status !== 'raw' ? `<span style="font-size:10px;color:var(--text2);margin-left:auto">${c.segment_count}段</span>` : ''}
        </div>`;
    }).join('');
  },

  async select(idx) {
    this.currentIdx = idx;
    this.selectedSegIdx = null;

    try {
      const data = await API.get(`/projects/${this.projectId}/chapters/${idx}`);
      this._cachedChapter = data;  // 缓存供 playSegment 使用
      this.renderDetail(data);
    } catch (e) {
      App.toast('加载章节失败: ' + e.message, 'error');
    }

    // 更新列表高亮
    this.loadList();
  },

  renderDetail(chapter) {
    document.getElementById('chapter-title').textContent = chapter.title;

    const badge = document.getElementById('chapter-status');
    badge.textContent = this.statusLabel(chapter.status);
    badge.className = 'status-badge ' + chapter.status;

    const editor = document.getElementById('segment-editor');
    if (!chapter.segments || chapter.segments.length === 0) {
      editor.innerHTML = `
        <div class="no-data">
          <p>该章节尚未结构化处理</p>
          <p style="font-size:12px;color:var(--text2);margin-top:8px">
            原文共 ${chapter.raw_text.length} 字符
          </p>
          <button class="btn btn-primary" style="margin-top:12px" onclick="Chapter.structure()">
            🤖 开始结构化处理
          </button>
        </div>`;
      return;
    }

    const self = this;
    editor.innerHTML = `
      <table class="seg-table">
        <thead>
          <tr>
            <th class="col-idx">#</th>
            <th class="col-type">类型</th>
            <th class="col-role">角色</th>
            <th class="col-emotion">情感</th>
            <th class="col-delay">延迟</th>
            <th class="col-text">文本</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          ${chapter.segments.map((s, i) => {
            const hasAudio = !!s.audio_path;
            const isGenerating = self._generatingSeg === i;
            const delay = (s.delay != null) ? s.delay : 0.4;
            const delayLabel = delay >= 0.45 ? '长停顿' : (delay >= 0.35 ? '中停顿' : '短停顿');
            const delayColor = delay >= 0.45 ? 'var(--orange)' : (delay >= 0.35 ? 'var(--accent)' : 'var(--text2)');
            return `
            <tr class="${self.selectedSegIdx === i ? 'selected' : ''}"
                onclick="Chapter.selectSegment(${i})">
              <td class="col-idx">${s.index}</td>
              <td class="col-type"><span class="type-tag ${s.type}">${s.type === 'narration' ? '旁白' : '对话'}</span></td>
              <td class="col-role">${s.speaker_name || '-'}</td>
              <td class="col-emotion"><span class="emotion-tag">${s.emotion || '-'}</span></td>
              <td class="col-delay"><span style="color:${delayColor};font-size:11px" title="${delayLabel}">${delay.toFixed(2)}s</span></td>
              <td class="col-text" title="${self.escapeHtml(s.text)}">${self.escapeHtml(s.text)}</td>
              <td class="col-actions">
                <div class="seg-actions">
                  ${isGenerating
                    ? `<button class="btn btn-sm btn-generating" disabled onclick="event.stopPropagation()">⏳ 生成中...</button>`
                    : `<button class="btn btn-sm btn-synth"
                              onclick="event.stopPropagation();Chapter.synthesizeSegment(${i})"
                              title="${hasAudio ? '重新生成（可控克隆模式）' : '点击生成语音'}">
                        ${hasAudio ? '🔄 重新生成' : '🎙 生成语音'}
                      </button>`
                  }
                  ${hasAudio
                    ? `<button class="btn btn-sm btn-play"
                              onclick="event.stopPropagation();Chapter.playSegment(${i})"
                              title="点击试听">▶ 试听</button>`
                    : ''
                  }
                </div>
              </td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>`;
  },

  selectSegment(idx) {
    this.selectedSegIdx = idx;
    // 重新渲染高亮
    this.select(this.currentIdx);
  },

  async structure() {
    if (this.currentIdx === null) {
      App.toast('请先选择一个章节', 'error');
      return;
    }

    // 显示加载状态
    const editor = document.getElementById('segment-editor');
    editor.innerHTML = `
      <div class="no-data" id="structure-progress">
        <div class="spinner-center"></div>
        <p style="margin-top:12px;font-weight:500">正在进行结构化处理...</p>
        <p style="font-size:12px;color:var(--text2);margin-top:4px">AI 正在分析章节文本，识别角色和情感</p>
      </div>`;
    App.setStatus('结构化处理中...');

    try {
      const data = await API.post(
        `/projects/${this.projectId}/chapters/${this.currentIdx}/structure`
      );
      App.setStatus('就绪');
      App.toast(`结构化完成！共 ${data.segment_count} 段`, 'success');
      // 重新加载项目数据以获取新角色
      await App.refresh();
      this.select(this.currentIdx);
    } catch (e) {
      App.setStatus('就绪');
      App.toast('结构化失败: ' + e.message, 'error');
      // 恢复空状态
      this.select(this.currentIdx);
    }
  },

  async synthesize() {
    if (this.currentIdx === null) {
      App.toast('请先选择一个章节', 'error');
      return;
    }

    App.toast('正在TTS合成...', 'success');
    App.setStatus('批量合成中...');

    // 先标记所有未生成条目为"等待中"
    this._generatingAll = true;
    this.rerenderCurrent();

    try {
      const resp = await fetch(
        `/api/v1/projects/${this.projectId}/chapters/${this.currentIdx}/synthesize`,
        { method: 'POST' }
      );

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: '合成失败' }));
        throw new Error(err.detail);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 保留不完整的行

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            this.handleSynthesizeProgress(data);
          }
        }
      }
    } catch (e) {
      App.toast('合成失败: ' + e.message, 'error');
    } finally {
      this._generatingAll = false;
      App.setStatus('就绪');
    }
  },

  handleSynthesizeProgress(data) {
    if (data.status === 'skip') {
      // 已生成，跳过 — 无需操作，按钮本来就是"重新生成"
      return;
    }

    if (data.status === 'done') {
      App.toast(`合成完成！共 ${data.total} 条`, 'success');
      // 刷新完整章节数据
      this.rerenderCurrentDetail();
      return;
    }

    if (data.status === 'ok') {
      // 单条完成，局部更新该行
      this.updateSegmentRow(data.segment_index);
      App.setStatus(`已合成 ${data.segment_index + 1} 条`);
    }

    if (data.status === 'error') {
      console.error(`段 ${data.segment_index} 合成失败:`, data.error);
    }
  },

  async updateSegmentRow(segIdx) {
    // 重新获取完整章节数据
    try {
      const data = await API.get(`/projects/${this.projectId}/chapters/${this.currentIdx}`);
      this._cachedChapter = data;
      const seg = data.segments[segIdx];
      if (!seg) return;

      // 找到表格中对应行并更新操作列
      const tbody = document.querySelector('.seg-table tbody');
      if (!tbody) return;
      const rows = tbody.querySelectorAll('tr');
      if (segIdx >= rows.length) return;

      const row = rows[segIdx];
      const actionsTd = row.querySelector('.col-actions');
      if (!actionsTd) return;

      const hasAudio = !!seg.audio_path;
      actionsTd.innerHTML = `
        <div class="seg-actions">
          <button class="btn btn-sm btn-synth"
                  onclick="event.stopPropagation();Chapter.synthesizeSegment(${segIdx}, ${hasAudio})"
                  title="${hasAudio ? '重新生成（声音设计随机模式）' : '点击生成语音'}">
            ${hasAudio ? '🔄 重新生成' : '🎙 生成语音'}
          </button>
          ${hasAudio
            ? `<button class="btn btn-sm btn-play"
                      onclick="event.stopPropagation();Chapter.playSegment(${segIdx})"
                      title="点击试听">▶ 试听</button>`
            : ''
          }
        </div>`;

      // 更新章节列表的状态点
      this.loadList();
    } catch (e) {
      console.error('更新 segment 行失败:', e);
    }
  },

  async mergeAudio() {
    if (this.currentIdx === null) {
      App.toast('请先选择一个章节', 'error');
      return;
    }

    App.toast('正在合并音频...', 'success');

    try {
      const data = await API.post(
        `/projects/${this.projectId}/chapters/${this.currentIdx}/merge?speed=${this._playbackRate}`
      );
      const audioUrl = `/output/${data.audio_path}`;

      // 弹出播放/下载提示
      const chapter = this._cachedChapter;
      const title = chapter ? chapter.title : `章节${this.currentIdx}`;
      const msg = `合并完成！共 ${data.segment_count} 段音频。\n\n是否下载合并后的文件？`;
      if (confirm(msg)) {
        // 触发下载
        const a = document.createElement('a');
        a.href = audioUrl;
        a.download = `${title}_合并.wav`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }

      App.toast('合并完成！', 'success');
    } catch (e) {
      App.toast('合并失败: ' + e.message, 'error');
    }
  },

  async reset() {
    if (this.currentIdx === null) return;
    if (!confirm('确定要重置本章节吗？所有结构化数据将丢失。')) return;

    try {
      await API.del(`/projects/${this.projectId}/chapters/${this.currentIdx}/reset`);
      App.toast('章节已重置', 'success');
      await App.refresh();
      this.select(this.currentIdx);
    } catch (e) {
      App.toast('重置失败: ' + e.message, 'error');
    }
  },

  /* ========== 单条 Segment 合成 & 试听 ========== */

  async synthesizeSegment(segIdx) {
    if (this.currentIdx === null) return;

    // 标记生成中状态
    this._generatingSeg = segIdx;
    this.rerenderCurrent();

    App.setStatus(`正在生成第 ${segIdx + 1} 段语音...`);

    try {
      const resp = await fetch(
        `/api/v1/projects/${this.projectId}/chapters/${this.currentIdx}/segment/${segIdx}/synthesize`,
        { method: 'POST' }
      );

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: '合成失败' }));
        throw new Error(err.detail);
      }

      const data = await resp.json();
      const modeLabel = data.mode === 'controllable_clone' ? '可控克隆' : '声音设计';
      const sourceInfo = data.audio_source ? ` 音频源:${data.audio_source}` : '';
      const promptInfo = data.prompt_used ? ` 情感:${data.prompt_used}` : '';
      const randomInfo = data.random_modifier ? ` 🎲${data.random_modifier}` : '';
      const speakerInfo = data.speaker_name ? ` 角色:${data.speaker_name}` : '';
      App.toast(`生成成功 [${modeLabel}]${speakerInfo}${sourceInfo}${promptInfo}${randomInfo}`, 'success');

      // CRITICAL: 必须先清除生成状态，再触发重渲染，否则按钮始终显示"生成中..."
      this._generatingSeg = null;
      await this.rerenderCurrentDetail();
    } catch (e) {
      this._generatingSeg = null;
      App.toast('语音生成失败: ' + e.message, 'error');
    } finally {
      App.setStatus('就绪');
    }
  },

  playSegment(segIdx) {
    // 获取当前章节的 segment 数据
    const chapterData = this._cachedChapter;
    if (!chapterData || !chapterData.segments) return;

    const seg = chapterData.segments[segIdx];
    if (!seg || !seg.audio_path) {
      App.toast('该条目尚未生成语音', 'error');
      return;
    }

    // 停止当前播放
    if (this._audioPlayer) {
      this._audioPlayer.pause();
      this._audioPlayer = null;
    }

    // 创建新的 Audio 元素播放
    const audioUrl = `/output/${seg.audio_path}`;
    const audio = new Audio(audioUrl);
    audio.playbackRate = this._playbackRate;
    audio.play().catch(e => {
      App.toast('播放失败: ' + e.message, 'error');
    });
    this._audioPlayer = audio;

    // 播放结束后清理
    audio.onended = () => {
      this._audioPlayer = null;
    };
    audio.onerror = () => {
      App.toast('音频加载失败', 'error');
      this._audioPlayer = null;
    };
  },

  /* ========== 内部辅助 ========== */

  async rerenderCurrent() {
    if (this.currentIdx === null) return;
    this.select(this.currentIdx);
  },

  async rerenderCurrentDetail() {
    if (this.currentIdx === null) return;
    try {
      const data = await API.get(`/projects/${this.projectId}/chapters/${this.currentIdx}`);
      this._cachedChapter = data;
      this.renderDetail(data);
      this.loadList();
    } catch (e) {
      console.error('重新加载章节失败:', e);
    }
  },

  statusLabel(s) {
    const map = { raw: '未处理', structured: '已结构化', synthesized: '已合成' };
    return map[s] || s;
  },

  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },

  async loadSpeed() {
    try {
      const data = await API.get(`/projects/${this.projectId}/playback-speed`);
      this._playbackRate = parseFloat(data.speed) || 1.0;
      const slider = document.getElementById('speed-slider');
      const label = document.getElementById('speed-label');
      if (slider) slider.value = this._playbackRate;
      if (label) label.textContent = this._playbackRate.toFixed(2) + 'x';
    } catch (e) {
      this._playbackRate = 1.0;
    }
  },

  onSpeedSlider(value) {
    const rate = parseFloat(value);
    this._playbackRate = rate;
    const label = document.getElementById('speed-label');
    if (label) label.textContent = rate.toFixed(2) + 'x';

    // 对当前正在播放的音频实时生效
    if (this._audioPlayer && !this._audioPlayer.paused) {
      this._audioPlayer.playbackRate = rate;
    }

    // 延迟保存到后端（debounce）
    clearTimeout(this._speedSaveTimer);
    this._speedSaveTimer = setTimeout(async () => {
      try {
        await API.put(`/projects/${this.projectId}/playback-speed`, { speed: rate });
      } catch (e) { /* 静默失败 */ }
    }, 500);
  },

  async setSpeed(value) {
    // 保留兼容，映射旧的下拉框值
    const map = { slow: 0.7, normal: 1.0, fast: 1.3 };
    this.onSpeedSlider(map[value] || 1.0);
  },
};
