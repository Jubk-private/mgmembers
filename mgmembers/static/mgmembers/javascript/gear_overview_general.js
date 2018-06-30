(function($) {
  var lastFilterText,
      jobMap = {
        "warrior": "WAR",
        "monk": "MNK",
        "white mage": "WHM",
        "black mage": "BLM",
        "red mage": "RDM",
        "thief": "THF",
        "paladin": "PLD",
        "dark knight": "DRK",
        "beastmaster": "BST",
        "bard": "BRD",
        "ranger": "RNG",
        "samurai": "SAM",
        "ninja": "NIN",
        "dragoon": "DRG",
        "summoner": "SMN",
        "blue mage": "BLU",
        "corsair": "COR",
        "puppetmaster": "PUP",
        "dancer": "DNC",
        "scholar": "SCH",
        "geomancer": "GEO",
        "rune fencer": "RUN"
      },
      knownDrops = {
        "Fu: Niqmaddu Ring": "Warrior / Monk / Dark Knight / Samurai / Dragoon / Puppetmaster / Rune Fencer",
        "Fu: Shulmanu collar": "Beastmaster / Dragoon / Summoner / Puppetmaster",
        "Fu: Nisroch jerkin": "Beastmaster / Dragoon / Summoner / Puppetmaster",
        "Kyou: Enmerkar earring": "Beastmaster / Dragoon / Summoner / Puppetmaster",
        "Kyou: Iskur gorget": "Thief / Ranger / Ninja / Corsair",
        "Kyou: Udug jacket": "Beastmaster / Summoner / Puppetmaster",
        "Kei: Ammurapi shield": "White Mage / Black Mage / Red Mage / Bard / Summoner / Scholar / Geomancer",
        "Kei: Lugalbanda earring": "Black Mage / Summoner / Scholar / Geomancer",
        "Kei: Shamash robe": "White Mage / Black Mage / Red Mage / Blue Mage / Scholar / Geomancer",
        "Gin: Yamarang": "Thief / Ninja / Dancer / Rune Fencer",
        "Gin: Dingir ring": "Thief / Ranger / Ninja / Corsair",
        "Gin: Ashera harness": "Monk / Thief / Bard / Ninja / Dancer / Rune Fencer",
        "Kin: Utu grip": "Warrior / Dark Knight / Samurai / Dragoon / Rune Fencer",
        "Kin: Ilabrat ring": "Monk / White Mage / Red Mage / Thief / Beastmaster / Bard / Ranger / Samurai / Ninja / Blue Mage / Corsair / Dancer / Rune Fencer",
        "Kin: Dagon breastplate": "Warrior / Paladin / Dark Knight / Samurai / Dragoon",
        "Ou: Regal belt": "SMN",
        "Ou: Regal captain's gloves": "Warrior / Monk / Dark Knight / Samurai / Puppetmaster",
        "Ou: Regal cuffs": "White Mage / Black Mage / Red Mage / Summoner / Blue Mage / Scholar / Geomancer",
        "Ou: Regal earring": "White Mage / Black Mage / Red Mage / Bard / Blue Mage / Scholar / Geomancer",
        "Ou: Regal gauntlets": "Paladin / Rune Fencer",
        "Ou: Regal gem": "RDM",
        "Ou: Regal gloves": "Thief / Beastmaster / Bard / Ranger / Ninja / Dragoon / Corsair / Dancer",
        "Ou: Regal necklace": "COR",
        "Ou: Regal ring": "Warrior / Monk / Thief / Paladin / Dark Knight / Beastmaster / Ranger / Samurai / Ninja / Dragoon / Corsair / Puppetmaster / Dancer / Rune Fencer",
        "Glassy Craver: Nusku shield": "Ranger / Corsair",
        "Glassy Craver: Sherida earring": "Monk / Red Mage / Thief / Beastmaster / Ranger / Dragoon / Dancer / Rune Fencer",
        "Glassy Craver: Anu torque": "Monk / Red Mage / Thief / Beastmaster / Ranger / Dragoon / Dancer / Rune Fencer",
        "Glassy Gorger: Kishar ring": "White Mage / Black Mage / Red Mage / Paladin / Dark Knight / Bard / Ninja / Summoner / Blue Mage / Corsair / Scholar / Geomancer / Rune Fencer",
        "Glassy Gorger: Enki strap": "White Mage / Black Mage / Red Mage / Bard / Summoner / Scholar / Geomancer",
        "Glassy Gorger: Erra pendant": "White Mage / Black Mage / Red Mage / Paladin / Dark Knight / Summoner / Blue Mage / Scholar / Geomancer / Rune Fencer",
        "Glassy Thinker: Adad amulet": "Beastmaster / Dragoon / Summoner / Puppetmaster",
        "Glassy Thinker: Knobkierrie": "Warrior / Monk / Dark Knight / Samurai / Dragoon / Rune Fencer",
        "Glassy Thinker: Adapa shield": "Warrior / Dark Knight / Beastmaster"
      },
      knownDropSortedKeys = $.map(
        knownDrops, function(k, v) { return v; }
      ).sort();

  $('#jobsfilterform input').on("change", function() {
    var jobsSelected = false,
        activeJobs = {},
        primaryJobs = [],
        seenPrimary = {},
        secondaryJobs = [],
        seenSecondary = {};
    $.each($('#jobsfilterform input:checked'), function() {
      jobsSelected = true;
      activeJobs[$(this).val()] = true;
    });
    if(jobsSelected) {
      $.each($('#jobstablebody th'), function() {
        var $this = $(this),
            $parent = $this.parent(),
            job = $this.text();
        if(activeJobs[job]) {
          $parent.show();
          $.each(
            $parent.find("td.primaryjobs").first().text().split(/,\s*/),
            function() {
              if(this.length && !seenPrimary[this]) {
                primaryJobs.push(this)
                seenPrimary[this] = true;
              }
            }
          )
          $.each(
            $parent.find("td.secondaryjobs").first().text().split(/,\s*/),
            function() {
              if(this.length  && !seenSecondary[this]) {
                secondaryJobs.push(this)
                seenSecondary[this] = true;
              }
            }
          )
        } else {
          $parent.hide();
        }
      });
    } else {
      $('#jobstablebody tr').show();
    }
    primaryJobs.sort()
    secondaryJobs.sort()
    $('#primary-jobs-output').text(primaryJobs.join(", "));
    $('#secondary-jobs-output').text(secondaryJobs.join(", "));
  });
  $('#clear-filter-button').on('click', function() {
    $('#jobsfilterform input.form-check-input').each(function() {
      $(this).prop("checked", false);
    });
    $('#jobsfilterform input.form-check-input').last().trigger("change");
    return false;
  });
  function textToCheckboxes(text) {
    var values = text.toLowerCase().split(/\s*[^\w\s]\s*/)
        selectedMap = {};

    // Save whats chosen
    $.each(values, function(index, value) {
      value = jobMap[value] || value.toUpperCase();
      selectedMap[value] = true;
    });

    $('#jobsfilterform input.form-check-input').each(function() {
      if(selectedMap[$(this).val()]) {
        $(this).prop("checked", true);
      } else {
        $(this).prop("checked", false);
      }
    });
    $('#jobsfilterform input.form-check-input').last().trigger("change");
  }
  function updateFromFilterText() {
    var val = $(this).val();

    if(lastFilterText != val) {
      lastFilterText = val;
      textToCheckboxes(val);
    }
  }
  $('#smartfilter').on('change', updateFromFilterText);
  $('#smartfilter').on('keyup', updateFromFilterText);
  var $knowndrops = $('#knowndrops');
  $.each(knownDropSortedKeys, function(index, value) {
    $knowndrops.append(
      $('<option>').attr("value", knownDrops[value]).text(value)
    );
  });
  $knowndrops.on("change", function() { textToCheckboxes($(this).val()); });

})(jQuery);
