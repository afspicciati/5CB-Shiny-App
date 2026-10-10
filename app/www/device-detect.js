// www/device-detect.js
$(document).on('shiny:connected', function () {
  // Check if screen width is less than 768px (standard mobile breakpoint)
  var isMobile = window.matchMedia('(max-width: 767px)').matches;
  Shiny.setInputValue('is_mobile', isMobile);
});
