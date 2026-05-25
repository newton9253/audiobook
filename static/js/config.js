/* 配置管理 */

const Config = {

  async load() {
    try {
      const data = await API.get('/config');
      this.fillForm(data);
    } catch (e) {
      console.error('加载配置失败:', e);
    }
  },

  fillForm(data) {
    const llm = data.llm || {};

    document.getElementById('cfg-llm-provider').value = llm.provider || 'openai';
    document.getElementById('cfg-openai-url').value = llm.openai?.base_url || '';
    document.getElementById('cfg-openai-key').value = llm.openai?.api_key || '';
    document.getElementById('cfg-openai-model').value = llm.openai?.model || 'gpt-4o';
    document.getElementById('cfg-tongyi-key').value = llm.tongyi?.api_key || '';
    document.getElementById('cfg-tongyi-model').value = llm.tongyi?.model || 'qwen-plus';
    document.getElementById('cfg-zhipu-key').value = llm.zhipu?.api_key || '';
    document.getElementById('cfg-zhipu-model').value = llm.zhipu?.model || 'glm-4';

    const tts = data.tts || {};
    document.getElementById('cfg-tts-provider').value = tts.provider || 'voxcpm2';
    document.getElementById('cfg-tts-url').value = tts.voxcpm2?.base_url || 'http://localhost:5022';

    this.onProviderChange();
  },

  onProviderChange() {
    const p = document.getElementById('cfg-llm-provider').value;
    document.getElementById('cfg-llm-openai').style.display = p === 'openai' ? '' : 'none';
    document.getElementById('cfg-llm-tongyi').style.display = p === 'tongyi' ? '' : 'none';
    document.getElementById('cfg-llm-zhipu').style.display = p === 'zhipu' ? '' : 'none';
  },

  async save() {
    const data = {
      llm: {
        provider: document.getElementById('cfg-llm-provider').value,
        openai: {
          base_url: document.getElementById('cfg-openai-url').value,
          api_key: document.getElementById('cfg-openai-key').value,
          model: document.getElementById('cfg-openai-model').value,
        },
        tongyi: {
          api_key: document.getElementById('cfg-tongyi-key').value,
          model: document.getElementById('cfg-tongyi-model').value,
        },
        zhipu: {
          api_key: document.getElementById('cfg-zhipu-key').value,
          model: document.getElementById('cfg-zhipu-model').value,
        },
      },
      tts: {
        provider: document.getElementById('cfg-tts-provider').value,
        voxcpm2: {
          base_url: document.getElementById('cfg-tts-url').value,
        },
      },
    };

    try {
      await API.put('/config', data);
      App.toast('配置已保存', 'success');
      App.hideConfig();
      App.updateStatus();
    } catch (e) {
      App.toast('保存失败: ' + e.message, 'error');
    }
  },

  async testConnection() {
    await this.save(); // 先保存

    App.toast('测试 LLM 连接...', 'success');
    try {
      const result = await API.post('/config/test-llm');
      App.toast('LLM 连接成功: ' + (result.model || 'OK'), 'success');
      document.getElementById('status-llm').innerHTML =
        'LLM: <span class="status-ok">✓</span>';
    } catch (e) {
      App.toast('LLM 连接失败: ' + e.message, 'error');
      document.getElementById('status-llm').innerHTML =
        'LLM: <span class="status-err">✗</span>';
    }

    App.toast('测试 TTS 连接...', 'success');
    try {
      await API.post('/config/test-tts');
      App.toast('TTS 连接成功', 'success');
      document.getElementById('status-tts').innerHTML =
        'TTS: <span class="status-ok">✓</span>';
    } catch (e) {
      App.toast('TTS 连接失败: ' + e.message, 'error');
      document.getElementById('status-tts').innerHTML =
        'TTS: <span class="status-err">✗</span>';
    }
  },
};
