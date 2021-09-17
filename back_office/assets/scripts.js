window.dash_clientside = Object.assign({}, window.dash_clientside, {
  clientside: {
    get_edited_content: function (trigger, element_id) {
      var el = document.getElementById(element_id);
      var content = el.innerHTML;
      return content;
    },
  },
});
