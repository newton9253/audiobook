/* 声音设计 */

const VoiceDesign = {
  characterId: null,

  open(charId) {
    this.characterId = charId;

    // 从当前角色数据填充
    const el = document.getElementById('char-detail');
    API.get(`/projects/${Character.projectId}/characters`).then(data => {
      const char = data.characters.find(c => c.id === charId);
      if (char) {
        document.getElementById('vd-name').value = char.name;
        document.getElementById('vd-prompt').value = char.voice_description
          || char.voice?.prompt
          || '';
      }
    });

    document.getElementById('vd-result').style.display = 'none';
    document.getElementById('voice-design-modal').classList.add('show');
  },

  async generate() {
    const characterId = this.characterId;
    if (!characterId) return;

    const text = document.getElementById('vd-text').value;
    const prompt = document.getElementById('vd-prompt').value;

    App.toast('正在生成试听音频...', 'success');

    try {
      const data = await API.post(
        `/projects/${Character.projectId}/characters/${characterId}/voice-design`,
        { text, prompt }
      );

      // 显示音频（加时间戳防浏览器缓存）
      const resultDiv = document.getElementById('vd-result');
      const audio = document.getElementById('vd-audio');
      audio.src = `/output/${data.audio_path}?_=${Date.now()}`;
      resultDiv.style.display = 'block';
      App.toast('试听生成完成！', 'success');
    } catch (e) {
      App.toast('声音设计失败: ' + e.message, 'error');
    }
  },

  async apply() {
    const characterId = this.characterId;
    const prompt = document.getElementById('vd-prompt').value;

    try {
      await API.put(`/projects/${Character.projectId}/characters/${characterId}`, {
        voice_description: prompt,
        voice: { prompt: prompt },
      });
      App.toast('音色已应用！', 'success');
      document.getElementById('voice-design-modal').classList.remove('show');
      Character.renderDetail(characterId);
    } catch (e) {
      App.toast('应用失败: ' + e.message, 'error');
    }
  },
};
