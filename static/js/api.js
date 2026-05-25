/* API 请求封装 */

const API = {
  base: '/api/v1',

  async request(method, path, body = null) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);

    const resp = await fetch(`${this.base}${path}`, opts);
    const data = await resp.json();

    if (!resp.ok) {
      throw new Error(data.detail || data.message || '请求失败');
    }
    return data;
  },

  get(path) { return this.request('GET', path); },
  post(path, body) { return this.request('POST', path, body); },
  put(path, body) { return this.request('PUT', path, body); },
  del(path) { return this.request('DELETE', path); },

  // 文件上传
  async upload(path, file) {
    const form = new FormData();
    form.append('file', file);
    const resp = await fetch(`${this.base}${path}`, { method: 'POST', body: form });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || '上传失败');
    return data;
  },
};
