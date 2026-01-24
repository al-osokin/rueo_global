
const routes = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', component: () => import('pages/Index.vue') },
      { path: 'pri', name:'aboutMain', component: () => import('pages/pri.vue') },
      { path: 'pri/:page', name:'about', component: () => import('pages/pri.vue') },
      { path: 'gram', name:'grammarMain', component: () => import('pages/gram.vue') },
      { path: 'gram/:page', name:'grammar', component: () => import('pages/gram.vue') },
      { path: 'sercxo', name:'dictionaryEmpty', component: () => import('pages/Index.vue') },
      { path: 'sercxo/:word', name:'dictionary', component: () => import('pages/Index.vue') },
      { path: 'info', name:'team', component: () => import('pages/info.vue') },
      { path: 'donaci', name:'donate', component: () => import('pages/donaci.vue') },
      { path: 'guglo', name:'search', component: () => import('pages/guglo.vue') },
      { path: 'social', name:'social', component: () => import('pages/social.vue') },
      { path: 'novajxoj', name:'news', component: () => import('pages/novajxoj.vue') },
      { path: 'admin/review', name:'adminReview', component: () => import('pages/AdminReview.vue') },


    ]
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/Error404.vue')
  }
]

export default routes
