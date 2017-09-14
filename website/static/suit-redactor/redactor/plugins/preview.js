if (!RedactorPlugins) var RedactorPlugins = {};

RedactorPlugins.preview = {
  init: function()
  {
    this.addBtnFirst('preview', 'Preview', function(){
      var previewTab = window.open("", "Preview"),
          url = window.location.pathname + 'preview/',
          $form = $('#entry_form');

      $.post(url, $form.serialize(), function(response){
        previewTab.document.write(response);
      }, "html");

    });
    this.changeBtnIcon('preview', 'clips');
  },
};
