(function($) {
    var destinations = {};

    $('#partybuilder table.dest-party td.dest-container').each(function() {
        var $this = $(this);
        destinations[$this.attr("data-role")] = $this;
    });

    $('#partybuilder span.event-job').on("click", function() {
        var $this = $(this),
            $dest = destinations[$this.attr("data-role")],
            $new_elem;

        if(!$dest) {
            return;
        }

        $this.hide();
        $new_elem = $('<span class="selected-char"/>')
            .attr("data-job", $this.attr("data-job"))
            .attr("data-char-name", $this.attr("data-char-name"))
            .attr("data-role", $this.attr("data-role"))
            .text(
                  $this.attr("data-char-name") +
                  " (" + $this.attr("data-job") + ")"
            );
        $new_elem.on("click", function() {
            var $this = $(this),
                name = $this.attr("data-char-name");
            $(
                '#partybuilder span.event-job[data-char-name=' + name + ']'
            ).show();
            $this.remove();
        });
        $dest.append($new_elem);
    });
})(jQuery);