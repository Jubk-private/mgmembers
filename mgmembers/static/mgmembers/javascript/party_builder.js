(function($) {
    var destinations = {};

    $('#partybuilder table.dest-party td.dest-container').each(function() {
        var $this = $(this);
        destinations[$this.attr("data-role")] = $this;
    });

    function update_count() {
        $('#partybuilder .party-count').text(
            "Count: " + $('#partybuilder span.selected-char').length
        );
    }

    $('#partybuilder span.event-job').on("click", function() {
        var $this = $(this),
            $dest = destinations[$this.attr("data-role")],
            charname = $this.attr("data-char-name"),
            pickers = $(
                '#partybuilder span.event-job[data-char-name=' + charname + ']'
            ),
            $new_elem;

        if(!$dest) {
            return;
        }

        pickers.hide();
        $new_elem = $('<span class="selected-char"/>')
            .attr("data-job", $this.attr("data-job"))
            .attr("data-char-name", charname)
            .attr("data-role", $this.attr("data-role"))
            .text(
                  $this.attr("data-char-name") +
                  " (" + $this.attr("data-job") + ")"
            );
        $new_elem.on("click", function() {
            $(this).remove();
            pickers.show();
            update_count();
        });
        $dest.append($new_elem);
        update_count();
    });
})(jQuery);