(function ($) {
  "use strict";

  function preloader() {
    if ($(".preloader").length) {
      $(".preloader").delay(100).fadeOut(500);
    }
  }

  // Navbar Sticky Handler
  var nav = $(".main-navbar");
  $(window).scroll(function () {
    if ($(this).scrollTop() > 80) {
      nav.addClass("fixed-header");
    } else {
      nav.removeClass("fixed-header");
    }
  });


  // Testimonial Carousel
  if ($(".testimonial-carousel").length) {
    $(".testimonial-carousel").owlCarousel({
      loop: true,
      margin: 0,
      dots: true,
      nav: false,
      rtl: true,
      autoplayHoverPause: false,
      autoplay: true,
      smartSpeed: 1500,
      responsive: {
        0: { items: 1 },
        768: { items: 2 },
        992: { items: 3 },
      },
    });
  }

  // Testimonial Carousel One
  if ($(".testimonial-carousel-one").length) {
    $(".testimonial-carousel-one").owlCarousel({
      loop: true,
      margin: 0,
      dots: true,
      nav: false,
      autoplay: true,
      rtl: true,
      smartSpeed: 1500,
      responsive: { 0: { items: 1 } },
    });
  }

  // Carousel One
  if ($(".carousel-one").length) {
    $(".carousel-one").owlCarousel({
      loop: true,
      margin: 0,
      rtl: true,
      dots: true,
      nav: false,
      autoplay: true,
      smartSpeed: 2000,
      responsive: { 0: { items: 1 } },
    });
  }

  // Counter / Funfact (Safely wrapped)
  if ($(".start-count").length) {
    $(".start-count").each(function () {
      var $this = $(this);
      $this.data("target", parseInt($this.html(), 10) || 0);
      $this.data("counted", false);
      $this.html("0");
    });

    $(window)
      .on("scroll", function () {
        var speed = 3000;
        $(".start-count").each(function () {
          var $this = $(this);
          if (
            $this.offset() &&
            !$this.data("counted") &&
            $(window).scrollTop() + $(window).height() >= $this.offset().top
          ) {
            $this.data("counted", true);
            $this.animate(
              { dummy: 1 },
              {
                duration: speed,
                step: function (now) {
                  var val = Math.round($this.data("target") * now);
                  $this.html(val);
                },
              },
            );
          }
        });
      })
      .triggerHandler("scroll");
  }

  // Gallery Filter
  $(".gallery-filter li").on("click", function (event) {
    $(this).siblings(".active").removeClass("active");
    $(this).addClass("active");
    event.preventDefault();
  });

  // Fancybox
  if ($(".lightbox-image").length && $.fn.fancybox) {
    $(".lightbox-image").fancybox({
      openEffect: "elastic",
      openSpeed: 250,
      closeEffect: "elastic",
    });
  }

// =====================================================
// SCROLL UP BUTTON - HANDS-ON HEALTH
// =====================================================

function updateScrollUp() {
    if ($(window).scrollTop() > 300) {
        $(".scrollup").addClass("active");
    } else {
        $(".scrollup").removeClass("active");
    }
}

// Check while scrolling
$(window).on("scroll", updateScrollUp);

// Check immediately when the page loads
updateScrollUp();

// Smooth scroll to top
$(".scrollup").on("click", function (event) {
    event.preventDefault();

    $("html, body").stop().animate(
        { scrollTop: 0 },
        700
    );
});
  
  $(window).on("load", function () {
    preloader();
  });
})(window.jQuery);

// Step Wizard Navigation
document.addEventListener("DOMContentLoaded", function () {
  let currentStep = 1;
  const totalSteps = 4;

  const nextBtns = document.querySelectorAll(".btn-next");
  const prevBtns = document.querySelectorAll(".btn-prev");

  nextBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      if (validateStep(currentStep)) {
        if (currentStep < totalSteps) {
          currentStep++;
          updateWizard();
        }
      }
    });
  });

  prevBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      if (currentStep > 1) {
        currentStep--;
        updateWizard();
      }
    });
  });

  function validateStep(step) {
    const activePanel = document.getElementById(`stepPanel${step}`);
    if (!activePanel) return true;

    const inputs = activePanel.querySelectorAll("input[required]");
    let valid = true;

    inputs.forEach((input) => {
      if (!input.checkValidity()) {
        input.reportValidity();
        valid = false;
      }
    });

    if (step === 2 && valid) {
      const checkboxes = activePanel.querySelectorAll(
        'input[type="checkbox"]:checked',
      );
      if (checkboxes.length === 0) {
        alert("Please select at least one service before proceeding.");
        valid = false;
      }
    }

    return valid;
  }

  function updateWizard() {
    document.querySelectorAll(".form-step-panel").forEach((panel) => {
      panel.classList.remove("active-panel");
    });
    const targetPanel = document.getElementById(`stepPanel${currentStep}`);
    if (targetPanel) targetPanel.classList.add("active-panel");

    const stepItems = document.querySelectorAll("#statusSidebar .step-item");
    stepItems.forEach((item) => {
      const stepNum = parseInt(item.getAttribute("data-step"));
      item.classList.remove("active", "completed");

      if (stepNum < currentStep) {
        item.classList.add("completed");
      } else if (stepNum === currentStep) {
        item.classList.add("active");
      }
    });
  }
});
