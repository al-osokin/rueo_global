<template>
  <div v-show="visible"
       id="timeline">
  </div>
</template>
<script>
export default {
  // name: 'ComponentName',

  data() {
    return {
      visible: true,

    };
  },
  mounted() {
    // twitter timeline widget
    let p = /^http:/.test(document.location) ? 'http' : 'https';
    window.twttr = (function(d, s, id) {
      let js, fjs = d.getElementsByTagName(s)[0],
        t = window.twttr || {};
      if (d.getElementById(id)) return t;
      js = d.createElement(s);
      js.async = true;
      js.id = id;
      js.src = p + '://platform.twitter.com/widgets.js';
      fjs.parentNode.insertBefore(js, fjs);
      // document.head.prepend(js);
      t._e = [];
      t.ready = function(f) {
        t._e.push(f);
      };

      return t;
    }(document, 'script', 'twitter-wjs'));
    //добавляем стили к twitter-timeline

    window.twttr.ready(() => {
        // console.log('ready');
        twttr.widgets.createTimeline(
          {
            sourceType: 'profile',
            screenName: 'Vortaristo',
          },
          document.getElementById('timeline'),
          {
            height: '600',
            related: 'Vortaristo',
            chrome: 'transparent',
            lang: 'ru',
            dnd: 'true',
            'border-color': '#324D5B85',

          }).then(function(el) {
        });
        this.$nextTick(function() {
          window.twttr.widgets.load();
          window.twttr.events.bind(
            'loaded',
            function(event) {
              event.widgets.forEach(function(widget) {
                // console.log('loaded');

                // console.log("Created widget", widget.id);
                const twitterWrapper = document.getElementById(widget.id);

                const iframeContent = twitterWrapper.contentDocument;
                iframeContent.head.innerHTML = iframeContent.head.innerHTML +
                  '<style type="text/css">.timeline-Tweet-text   {font-size: 14px !important; line-height: 20px !important; color: #6a6a6a !important} .timeline-Header-title {color: #324d5b !important} .timeline-Header {padding: 10px 0;}</style>';

              });
            },
          );

          window.twttr.events.bind(
            'rendered',
            function(event) {
              // console.log('rendered');
              const twitterWrapper = document.getElementById(event.target.id);
              const iframeContent = twitterWrapper.contentDocument;
              iframeContent.head.innerHTML = iframeContent.head.innerHTML +
                '<style type="text/css">.timeline-Tweet-text   {font-size: 14px !important; line-height: 20px !important; color: #6a6a6a !important} .timeline-Header-title {color: #324d5b !important} .timeline-Header {padding: 10px 0;}</style>';
            },
          );

        });

      },
    );
  },
  beforeUnmount() {
    [...document.getElementById('timeline').children].forEach(function(el) {
      el.remove();
    });
  },
};
</script>
