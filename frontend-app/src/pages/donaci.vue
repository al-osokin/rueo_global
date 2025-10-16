<template>
  <q-page padding>
    <div class="wrap">
      <h1>Поддержите нас</h1>
      <p>
        Работа над словарём — долгое и&nbsp;неблагодарное занятие. Одно только
        содержание сервера обходится более чем в&nbsp;двадцать пять тысяч рублей
        в&nbsp;год.
      </p>
      <p>
        Если вы находите наш проект нужным и&nbsp;хотите оказать нам поддержку,
        воспользуйтесь одним из способов сделать это.
      </p>
      <h2>Ежемесячная подписка</h2>

      <p>
        <a
          class="text-h6 link-style"
          href="https://boosty.to/kondratjev-vortaroj"
          target="_blank"
          >Платформа Boosty
          <q-img src="images/boostyColor.png" width="90px" />
        </a>
      </p>
      <h2>Разовое пожертвование</h2>
      <p>
        <a
          class="text-h6 link-style"
          href="https://boosty.to/kondratjev-vortaroj/donate"
          target="_blank"
          >Платформа Boosty <q-img src="images/boostyColor.png" width="90px" />
        </a>
      </p>

      <p class="text-h6 link-style">
        Кошелёк Юmoney (бывший Яндекс.деньги)
        <q-img src="images/yoomoney.svg" width="90px" />
      </p>
      <p><strong>410016607596</strong></p>
      <p>
        <iframe
          allowtransparency="true"
          frameborder="0"
          height="250"
          scrolling="no"
          src="https://yoomoney.ru/quickpay/shop-widget?writer=seller&amp;targets=%D0%9F%D0%BE%D0%B6%D0%B5%D1%80%D1%82%D0%B2%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5%20%D0%BD%D0%B0%20%D1%81%D0%BB%D0%BE%D0%B2%D0%B0%D1%80%D0%B8%20%D0%91%D0%BE%D1%80%D0%B8%D1%81%D0%B0%20%D0%9A%D0%BE%D0%BD%D0%B4%D1%80%D0%B0%D1%82%D1%8C%D0%B5%D0%B2%D0%B0&amp;targets-hint=%D0%9F%D0%BE%D0%B6%D0%B5%D1%80%D1%82%D0%B2%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5%20%D0%BD%D0%B0%20%D1%81%D0%BB%D0%BE%D0%B2%D0%B0%D1%80%D0%B8%20%D0%91%D0%BE%D1%80%D0%B8%D1%81%D0%B0%20%D0%9A%D0%BE%D0%BD%D0%B4%D1%80%D0%B0%D1%82%D1%8C%D0%B5%D0%B2%D0%B0&amp;default-sum=100&amp;button-text=14&amp;payment-type-choice=on&amp;mobile-payment-type-choice=on&amp;hint=&amp;successURL=&amp;quickpay=shop&amp;account=410016607596"
          width="100%"
        ></iframe>
      </p>
    </div>
  </q-page>
</template>
<script>
import { createMetaMixin } from "quasar";

export default {
  // name: 'PageName',
  mixins: [
    createMetaMixin(function () {
      return {
        title: `Эсперанто словари Бориса Кондратьева | Поддержать проект`,
        meta: {
          description: {
            name: "description",
            content:
              "Описание грамматики эсперанто из Больших эсперанто-русского и русско-эсперантского словарей Бориса Кондратьева. Удобный поиск по словарям. Эсперанто-русский словарь, русско-эсперантский словарь онлайн",
          },
          keywords: {
            name: "keywords",
            content:
              "эсперанто, словарь эсперанто онлайн, грамматика, грамматика эсперанто онлайн",
          },
          equiv: {
            "http-equiv": "Content-Type",
            content: "text/html; charset=UTF-8",
          },
        },
      };
    }),
  ],
};
</script>
