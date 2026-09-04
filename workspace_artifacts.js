(function () {
  'use strict';

  const API = () => `${window.BITEY_API_BASE || ''}/api/v1`;
  let activeWorkspace = null;

  async function request(path, options) {
    const response = await fetch(API() + path, {
      headers: { 'Content-Type': 'application/json', ...(options && options.headers || {}) },
      ...options,
    });
    if (!response.ok) throw new Error('Bitey API ' + response.status);
    return response.json();
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  function artifactList(execution) {
    if (!execution) return [];
    if (Array.isArray(execution.artifacts) && execution.artifacts.length) return execution.artifacts;
    if (Array.isArray(execution.deliverables)) {
      return execution.deliverables.map(function (item) {
        const artifact = item.result && item.result.artifact;
        return artifact ? { ...artifact, capability: item.capability, result: item.result } : null;
      }).filter(Boolean);
    }
    return execution.artifact ? [execution.artifact] : [];
  }

  function artifactCard(artifact, index) {
    const type = artifact.artifact_type || artifact.type || 'artifact';
    const content = artifact.content && typeof artifact.content === 'object'
      ? artifact.content.content || '' : (artifact.content || '');
    const status = artifact.status || 'ready';
    const title = artifact.name || ({document:'Documento',presentation:'Presentación',spreadsheet:'Hoja de cálculo',code:'Código'}[type] || 'Artefacto');
    const format = artifact.content && typeof artifact.content === 'object' ? artifact.content.format : artifact.format;
    return '<article class="artifact-card" data-artifact-index="' + index + '">' +
      '<div class="artifact-card-head"><span class="artifact-type">' + escapeHtml(type) + '</span>' +
      '<span class="artifact-status">' + escapeHtml(status) + '</span></div>' +
      '<h4>' + escapeHtml(title) + '</h4>' +
      '<p class="artifact-format">' + escapeHtml(format || 'Bitey artifact') + '</p>' +
      '<div class="artifact-actions"><button type="button" data-artifact-preview="' + index + '">Vista previa</button></div>' +
      '<pre class="artifact-preview" hidden>' + escapeHtml(content) + '</pre>' +
      '</article>';
  }

  function renderArtifacts(container, execution) {
    const artifacts = artifactList(execution);
    if (!artifacts.length) return;
    let panel = container.querySelector('.workspace-artifact-collection');
    if (!panel) {
      panel = document.createElement('section');
      panel.className = 'workspace-artifact-collection';
      container.appendChild(panel);
    }
    panel.innerHTML = '<div class="artifact-collection-head"><div><span class="workspace-eyebrow">RESULTADOS</span><h3>Artefactos de Bitey</h3></div><span class="artifact-count">' + artifacts.length + ' salida' + (artifacts.length === 1 ? '' : 's') + '</span></div>' +
      '<div class="artifact-grid">' + artifacts.map(artifactCard).join('') + '</div>';
    panel.querySelectorAll('[data-artifact-preview]').forEach(function (button) {
      button.addEventListener('click', function () {
        const preview = panel.querySelector('[data-artifact-index="' + button.dataset.artifactPreview + '"] .artifact-preview');
        if (preview) preview.hidden = !preview.hidden;
        button.textContent = preview && preview.hidden ? 'Vista previa' : 'Ocultar vista previa';
      });
    });
  }

  function enhanceModal() {
    const modal = document.querySelector('.workspace-modal, .bitey-workspace-modal, [data-workspace-modal]');
    if (!modal) return;
    const result = modal.querySelector('.workspace-result');
    if (!result) return;
    const raw = result.dataset.execution;
    if (!raw) return;
    try { renderArtifacts(result, JSON.parse(raw)); } catch (_) { /* original UI remains intact */ }
  }

  async function createAndRun(prompt, workspaceId) {
    const task = await request('/workspaces/' + encodeURIComponent(workspaceId) + '/tasks', {
      method: 'POST', body: JSON.stringify({ prompt: prompt, title: prompt.slice(0, 80) })
    });
    return request('/workspaces/' + encodeURIComponent(workspaceId) + '/tasks/' + encodeURIComponent(task.id) + '/run', { method: 'POST' });
  }

  async function ensureWorkspace() {
    if (activeWorkspace) return activeWorkspace;
    const data = await request('/workspaces');
    const list = data.workspaces || data.items || [];
    activeWorkspace = list[0];
    if (!activeWorkspace) activeWorkspace = await request('/workspaces', { method: 'POST', body: JSON.stringify({ name: 'Bitey Workspace' }) });
    return activeWorkspace;
  }

  window.BiteyWorkspaceArtifacts = {
    render: renderArtifacts,
    artifactList: artifactList,
    createAndRun: async function (prompt) {
      const workspace = await ensureWorkspace();
      return createAndRun(prompt, workspace.id);
    }
  };

  document.addEventListener('click', function (event) {
    if (event.target.closest('[data-workspace]')) setTimeout(enhanceModal, 0);
  });
})();
