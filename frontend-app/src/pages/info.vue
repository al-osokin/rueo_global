<template>
  <q-page class="wrap" padding>
    <!-- content -->
    <div :class="{ 'no-wrap': $q.screen.gt.xs }" class="flex justify-between">
      <div>
        <h1>Команда</h1>
        <p v-for="(i, index) in skipo" :key="index">
          <img
            :alt="i.alt"
            :src="require(`../assets/info/${i.img}`)"
            class="circle"
          /><br />
          {{ i.desc }}<br />
          <a :href="`mailto:${i.mail}?subject=${i.subj}`">{{ i.mail }}</a>
        </p>
        <h2>Программисты</h2>
        <p v-for="(i, index) in programistoj" :key="index">
          <img
            :alt="i.alt"
            :src="require(`../assets/info/${i.img}`)"
            class="circle"
          /><br />
          {{ i.desc }}<br />
          <a :href="`mailto:${i.mail}?subject=${i.subj}`">{{ i.mail }}</a>
        </p>
        <h2>Научные консультанты</h2>
        <p v-for="(i, index) in konsilantoj" :key="index">
          <img
            :alt="i.alt"
            :src="require(`../assets/info/${i.img}`)"
            class="circle"
          /><br />
          {{ i.desc }}
        </p>
      </div>
      <div :class="{ 'order-first': $q.screen.lt.sm }">
        <h3>Меценаты проекта</h3>
        <ul>
          <li v-for="(i, index) in mecenatoj" class="text-no-wrap" :key="index">
            {{ i }}
          </li>
        </ul>
      </div>
    </div>
    <div>
      <h2>Обратная связь</h2>
      <p>
        Если в&nbsp;словарях или на&nbsp;этом сайте вы обнаружили ошибки, если
        у&nbsp;вас есть предложения по&nbsp;улучшению или вопросы, можно
        использовать один из многочисленных вариантов обратной связи.
      </p>
      <ul>
        <li>
          Нажмите зелёный ярлычок «Оставьте свой отзыв» с&nbsp;правой стороны
          экрана.
        </li>
        <li>
          Воспользуйтесь системой «Орфус»: выделите замеченную ошибку
          в&nbsp;окне браузера и нажмите клавиши Ctrl и Enter. Откроется окно,
          в&nbsp;котором вы можете прокомментировать ошибку.<br />
          <em>
            Обратите внимание на следующее: если в&nbsp;процитированном для
            отправки нам фрагменте текста нет&nbsp;заголовка статьи (словарного
            слова), то вы очень поможете нам исправить ошибку, указав слово,
            о&nbsp;котором идёт речь.
          </em>
        </li>
        <li>
          Наконец, вы можете написать сообщение и отправить его по электронной
          почте любому участнику проекта. Наши адреса перечислены на странице
          «Команда».
        </li>
      </ul>
      <p>Пишите, пожалуйста, ваше мнение важно.</p>
      <h2>Отзывы и предложения</h2>
      <p>
        Книга жалоб и предложений онлайн-версии большого эсперанто-русского — и
        в ближайшей перспективе русско-эсперантского — словарей Бориса
        Кондратьева.
      </p>
      <p>
        Здесь вы можете сообщить нам о замеченных в словарной статье ошибках или
        оставить пожелания по дизайну и функциональным возможностям сайта.
      </p>
      <p>
        <a href="http://vortaro.reformal.ru/" target="_blank"
          >Vortaro.Reformal.ru</a
        >
      </p>
      <p>
        И&nbsp;последнее. Даже если вы не&nbsp;нашли ошибок и не&nbsp;имеете
        никаких замечаний, а&nbsp;просто считаете, что мы всё это время
        трудились не&nbsp;зря, —
      </p>
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
      <p>
        <iframe
          allowtransparency="true"
          frameborder="0"
          height="250"
          scrolling="no"
          src="https://yoomoney.ru/quickpay/shop-widget?writer=seller&targets=%D0%9F%D0%BE%D0%B6%D0%B5%D1%80%D1%82%D0%B2%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5%20%D0%BD%D0%B0%20%D1%81%D0%BB%D0%BE%D0%B2%D0%B0%D1%80%D0%B8%20%D0%91%D0%BE%D1%80%D0%B8%D1%81%D0%B0%20%D0%9A%D0%BE%D0%BD%D0%B4%D1%80%D0%B0%D1%82%D1%8C%D0%B5%D0%B2%D0%B0&targets-hint=%D0%9F%D0%BE%D0%B6%D0%B5%D1%80%D1%82%D0%B2%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5%20%D0%BD%D0%B0%20%D1%81%D0%BB%D0%BE%D0%B2%D0%B0%D1%80%D0%B8%20%D0%91%D0%BE%D1%80%D0%B8%D1%81%D0%B0%20%D0%9A%D0%BE%D0%BD%D0%B4%D1%80%D0%B0%D1%82%D1%8C%D0%B5%D0%B2%D0%B0&default-sum=100&button-text=14&payment-type-choice=on&mobile-payment-type-choice=on&hint=&successURL=&quickpay=shop&account=410016607596"
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

  data() {
    return {
      mecenatoj: [
        "Денис Аристов",
        "Александр Басов",
        "Геннадий Басов",
        "Михаил Бронштейн",
        "Стас Бушуев",
        "Тимофей Вшивцев",
        "Татьяна Вшивцева",
        "Диляра Гадирова",
        "Гафур Газизов",
        "Татьяна Глазница",
        "Игорь Денисов",
        "Дмитрий Доценко",
        "Сергей Жилейкин",
        "Борис Зозуля",
        "Вячеслав Иванов",
        "Георгий Кеворкянц",
        "Иван Китайкин",
        "Сергей Кумков",
        "Виктор Лаптев",
        "Александр Лебедев",
        "Татьяна Лоскутова",
        "Елена Надикова",
        "Людмила Новикова",
        "Владимир Оплетаев",
        "Михаил Поворин",
        "Вячеслав Рождественский",
        "Анатолий Сидоров",
        "Олеся Соболевская",
        "Андрей Спасибожко",
        "Валентина Спицина",
        "Cергей Страшненко",
        "Александра Судакова",
        "Галина Терентьева",
        "Елена Успенская",
        "Пётр Федосов",
        "Валерия Цветкова",
        "Лариса Шапошникова",
        "Геннадий Шлепченко",
        "Денис",
        "Rotheran",
        "Pascal Dubourg Glatigny (Francio)",
        "Участники курсов Т.Г.Лоскутовой",
        "Rusia Esperantista Unio (REU)",
        "Sankt-Peterburga E-klubo «Kariljono»",
        "Moskva Esperanto-Asocio MASI",
        "Libroservo de Ĉelabinska E-klubo",
        "Tiĥvinaj Esperanto Metiejoj (TEMoj)",
        "Teknokomo",
      ],
      skipo: [
        {
          img: "Boris.jpg",
          alt: "Борис Кондратьев - автор словаря",
          mail: "vortaristo@gmail.com",
          subj: "Letero de la vortara paĝaro por la aŭtoro",
          desc: "Борис Кондратьев, автор словарей.",
        },
        {
          img: "Aleks.jpg",
          alt: "Александр Осокин - координатор проекта",
          mail: "alex.osokin@gmail.com",
          subj: "Letero de la vortara paĝaro por Aleks",
          desc: "Александр Осокин, редактор, координатор проекта.",
        },
      ],
      programistoj: [
        {
          img: "Ilya.jpg",
          alt: "Илья Муравьёв - программирование и поддержка сайта",
          mail: "muravev@yandex.ru",
          subj: "Pri la paĝaro",
          desc: "Илья Муравьёв, один из программеров.",
        },
        {
          img: "Vaganto.jpg",
          alt: "Владимир Романович - разработка адаптивной версии сайта",
          mail: "ibnteo@gmail.com",
          subj: "rueo",
          desc: "Владимир Романович, разработка адаптивной версии сайта.",
        },
        {
          img: "cemisovs.jpg",
          alt: "Егор Чемисов - мобильная версия",
          mail: "yegor.chemisov@gmail.com",
          subj: "ervo",
          desc: "Егор Чемисов, разработка Pocket-версии словарей, альфа-тестирование.",
        },
      ],
      konsilantoj: [
        {
          img: "Sosov.jpg",
          alt: "Евгений Сосов - консультант раздела математики",
          mail: "",
          subj: "",
          desc:
            "Евгений Сосов, доктор физико-математических наук, " +
            "доцент кафедры геометрии Казанского федерального университета. " +
            "Консультант по разделу математики.",
        },
        {
          img: "Mojhaev.jpg",
          alt: "Павел Можаев - консультант раздела медицины",
          mail: "",
          subj: "",
          desc:
            "Павел Можаев, преподаватель кафедры топографической анатомии и " +
            "оперативной хирургии Крымского государственного медицинского " +
            "университета. Член Академии эсперанто. " +
            "Консультант по разделу медицины и по общему словнику.",
        },
      ],
    };
  },
  mixins: [
    createMetaMixin(function () {
      return {
        title: `Эсперанто словари Бориса Кондратьева | Команда`,
        meta: {
          description: {
            name: "description",
            content:
              "Контактная информация для связи с автором словаря, координатором и разработчиками. Редакторы словаря и неравнодушные люди.",
          },
          keywords: {
            name: "keywords",
            content:
              "связь с автором, электронная почта Бориса Кондратьева, предложения, вопросы, редакторская работа, поддержка, спасибо",
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
<style scoped>
.circle {
  border-radius: 50% !important;
}
</style>
