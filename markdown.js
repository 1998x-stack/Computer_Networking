// MathJax configuration must run before the deferred MathJax loader.
window.MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\(', '\\)']],
    displayMath: [['$$', '$$'], ['\\[', '\\]']]
  },
  options: { renderActions: { addMenu: [0, '', ''] } }
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.hljs && typeof window.hljs.highlightAll === 'function') {
    window.hljs.highlightAll();
  }

  document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach((heading) => {
    heading.addEventListener('click', () => {
      heading.scrollIntoView({ behavior: 'smooth' });
    });
  });

  // All notes are plain text; never inject user-supplied HTML.
  document.querySelectorAll('.container p, .container li').forEach((element) => {
    element.addEventListener('dblclick', () => {
      if (element.querySelector('.comment-input-container')) return;

      const holder = document.createElement('div');
      holder.className = 'comment-input-container';
      const input = document.createElement('input');
      input.type = 'text';
      input.className = 'comment-input';
      input.placeholder = '输入你的评论并按回车';

      let finished = false;
      const finish = (save) => {
        if (finished) return;
        finished = true;
        const note = input.value.trim();
        if (save && note) {
          const comment = document.createElement('div');
          comment.className = 'comment';
          comment.textContent = note;
          element.appendChild(comment);
        }
        holder.remove();
      };

      input.addEventListener('blur', () => finish(true));
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          finish(true);
        } else if (event.key === 'Escape') {
          event.preventDefault();
          finish(false);
        }
      });

      holder.appendChild(input);
      element.appendChild(holder);
      input.focus();
    });
  });

  const saveButton = document.createElement('button');
  saveButton.type = 'button';
  saveButton.textContent = '保存文章与评论';
  saveButton.className = 'save-button';
  saveButton.addEventListener('click', saveContent);
  document.body.appendChild(saveButton);
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
}

function saveContent() {
  const article = document.querySelector('.container');
  if (!article) return;

  // Clone the article once: lists, code, formulas, images and comments are
  // preserved in document order. Do not re-append comments a second time.
  const copy = article.cloneNode(true);
  copy.querySelectorAll('script, .comment-input-container').forEach((node) => node.remove());

  // Export links and image paths relative to the original page, not the new file.
  copy.querySelectorAll('a[href], img[src]').forEach((node) => {
    const attr = node.tagName.toLowerCase() === 'img' ? 'src' : 'href';
    const value = node.getAttribute(attr);
    if (!value || value.startsWith('#') || /^(data:|mailto:|javascript:)/i.test(value)) return;
    try {
      node.setAttribute(attr, new URL(value, document.baseURI).href);
    } catch (_) {
      // Keep an unusual URL unchanged instead of breaking the export.
    }
  });

  const saved = [
    '<!doctype html>',
    '<html lang="' + escapeHtml(document.documentElement.lang || 'zh-CN') + '">',
    '<head><meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    '<title>' + escapeHtml(document.title || 'Computer Networking Notes') + '</title>',
    '<style>',
    'body{font:16px/1.7 system-ui,-apple-system,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#222}',
    'pre{overflow-x:auto;background:#f4f5f7;padding:1rem;border-radius:6px}',
    'code{overflow-wrap:anywhere}',
    'table{border-collapse:collapse;max-width:100%;display:block;overflow-x:auto}',
    'th,td{border:1px solid #bbb;padding:.4rem .65rem}',
    'img{max-width:100%;height:auto}',
    'blockquote{margin-left:0;padding-left:1rem;border-left:3px solid #888}',
    '.comment{padding:.4rem .75rem;border-left:3px solid #5c829d;background:#eef3f7;margin:.4rem 0}',
    '</style></head><body>',
    copy.outerHTML,
    '</body></html>'
  ].join('\n');

  const blob = new Blob([saved], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'article_with_comments.html';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
