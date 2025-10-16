<template>
  <q-page padding>
    <!-- content -->
    <div class="wrap">
      <h1>Поиск на сайте</h1>
      <p>Поиск по статьям на сайте. Для поиска слов в словаре, воспользуйтесь поисковой формой
        <router-link :to="{name:'dictionaryEmpty'}">веб-словаря.</router-link>
      </p>
      <hr>
      <br>
      <div class="gcse-search"></div>
    </div>
  </q-page>
</template>
<script>
import * as utils from 'src/utils';

export default {
  // name: 'PageName',
  mounted() {
    const cx = '007871939051575929768:fsfhs16cyvy';
    let p = /^http:/.test(document.location) ? 'http' : 'https';
    utils.head_script({src: p + '://cse.google.com/cse.js?cx=' + cx, async: true});

  },
  beforeUnmount() {
    const cx = '007871939051575929768:fsfhs16cyvy';
    let p = /^http:/.test(document.location) ? 'http' : 'https';
    utils.del_script(p + '://cse.google.com/cse.js?cx=' + cx);
    utils.del_orphan_script('google');
    utils.del_orphan_link('google');

  },
};
</script>
