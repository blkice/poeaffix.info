$(function() {
    $(".mod-group").hide();

    $(".mod-group-effect")
        .attr("role", "button")
        .css("cursor", "pointer")
        .on("click", function() {
            $(this)
                .toggleClass("active")
                .next(".mod-group").toggle("normal")
        });
});
