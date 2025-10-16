function head_script({src, id, async}) {
  if (document.querySelector('script[src=\'' + src + '\']')) { return; }
  let script = document.createElement('script');
  script.setAttribute('src', src);
  script.setAttribute('type', 'text/javascript');
  if (id) {
    script.setAttribute('id', id);
  }
  if (async) {
    script.async = async;
  }
  document.head.appendChild(script);
}

function body_script(src) {
  if (document.querySelector('script[src=\'' + src + '\']')) { return; }
  let script = document.createElement('script');
  script.setAttribute('src', src);
  script.setAttribute('type', 'text/javascript');
  document.body.appendChild(script);
}

function del_script(src) {
  let el = document.querySelector('script[src=\'' + src + '\']');
  if (el) { el.remove(); }
}

function del_orphan_script(name) {
  let list = document.querySelectorAll('script');
  let filteredList = [...list].filter(
    function(el) {return el.src.includes(name);});

  filteredList.forEach(function(el) {el.remove();});
}

function head_link(href) {
  if (document.querySelector('link[href=\'' + href + '\']')) { return; }
  let link = document.createElement('link');
  link.setAttribute('href', href);
  link.setAttribute('rel', 'stylesheet');
  link.setAttribute('type', 'text/css');
  document.head.appendChild(link);
}

function body_link(href) {
  if (document.querySelector('link[href=\'' + href + '\']')) { return; }
  let link = document.createElement('link');
  link.setAttribute('href', href);
  link.setAttribute('rel', 'stylesheet');
  link.setAttribute('type', 'text/css');
  document.body.appendChild(link);
}

function del_link(href) {
  let el = document.querySelector('link[href=\'' + href + '\']');
  if (el) { el.remove(); }
}

function del_orphan_link(name) {
  let list = document.querySelectorAll('link');
  let filteredList = [...list].filter(
    function(el) {return el.href.includes(name);});

  filteredList.forEach(function(el) {el.remove();});
}

export {
  head_script,
  body_script,
  del_script,
  head_link,
  body_link,
  del_link,
  del_orphan_script,
  del_orphan_link,
};
