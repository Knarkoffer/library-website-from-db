$(document).ready(function(){
  // Filter-box
  $("#filterBox").on("keyup", function() {
    var search_string = $(this).val().toLowerCase()
    if (search_string.length > 2) {
        console.log("Activating filter...")
        iterate_books(search_string)
    } else if (search_string.length == 0){
        if (on_mobile){
            hide_all_rows()
        } else {
            iterate_books(search_string)
        }

    }
  });
  
  //Filters
	$('th').each(function (column) {
		$(this).addClass('sortable').click(function () {
				var findSortKey = function ($cell) {
					return $cell.find('.sort-key').text().toUpperCase()+ ' ' + $cell.text().toUpperCase();

				};
				var sortDirection = $(this).is('.sorted-asc') ? -1 : 1;
				var $rows = $(this).parent().parent().parent().find('tbody tr').get();
				var bob = 0;
				//loop through all the rows and find
				$.each($rows, function (index, row) {
					row.sortKey = findSortKey($(row).children('td').eq(column));
				});

				//compare and sort the rows alphabetically or numerically
				$rows.sort(function (a, b) {                       
					if (a.sortKey.indexOf('-') == -1 && (!isNaN(a.sortKey) && !isNaN(a.sortKey))) {
						 //Rough Numeracy check                          
							
							if (parseInt(a.sortKey) < parseInt(b.sortKey)) {
								return -sortDirection;
							}
							if (parseInt(a.sortKey) > parseInt(b.sortKey)) {                                
								return sortDirection;
							}

					} else {
						if (a.sortKey < b.sortKey) {
							return -sortDirection;
						}
						if (a.sortKey > b.sortKey) {
							return sortDirection;
						}
					}
					return 0;
				});

				//add the rows in the correct order to the bottom of the table
				$.each($rows, function (index, row) {
					$('tbody').append(row);
					row.sortKey = null;
				});

				//identify the column sort order
				$('th').removeClass('sorted-asc sorted-desc');
				var $sortHead = $('th').filter(':nth-child(' + (column + 1) + ')');
				sortDirection == 1 ? $sortHead.addClass('sorted-asc') : $sortHead.addClass('sorted-desc');

				//identify the column to be sorted by
				$('td').removeClass('sorted').filter(':nth-child(' + (column + 1) + ')').addClass('sorted');
			});
		});
});

function iterate_books(search_string)
{
    var filtered_books = 0
    console.log("Searching for " + search_string);
    $( ".item" ).each(function(index) {
        if ($(this).text().toLowerCase().indexOf(search_string) > -1){
            //console.log("Match: " + $(this).text())
            $(this).show()
            filtered_books = filtered_books + 1
        } else {
            $(this).hide()
        }
    });
    $("#book_counter").text(filtered_books + " books")
    //

}

function hide_all_rows()
{
    console.log("Hiding all book rows");
    $( ".item" ).each(function(index) {
        $(this).hide()
    });
}