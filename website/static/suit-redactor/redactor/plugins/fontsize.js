if (!RedactorPlugins) var RedactorPlugins = {};

RedactorPlugins.fontsize = {
  init: function()
  {
    var fonts = [10, 11, 12, 14, 16, 18, 20, 24, 28, 30];
    var that = this;
    var dropdown = {};

    $.each(fonts, function(i, s)
    {
      dropdown['s' + i] = { title: s + 'px', callback: function() { that.setFontsize(s); } };
    });

    dropdown.remove = { title: 'Remove font size', callback: function() { that.resetFontsize(); } };

    this.addBtnFirst('fontsize', 'Change font size', false, dropdown);
    this.changeBtnIcon('fontsize', 'fullscreen');
  },
  setFontsize: function(size)
  {
    var code = this.getCode(),
      selectedHtml = this.getSelectedHtml(),
      updatedCode = code.replace(selectedHtml, "<span style='font-size:"+size+"px;'>" + selectedHtml + "</span>");

    if(updatedCode !== '') this.setCode(updatedCode);
  },
  resetFontsize: function()
  {
    $(this.getCurrentNode()).css('font-size', '');
  }
};
