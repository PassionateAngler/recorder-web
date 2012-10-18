/* Polish initialisation for the jQuery UI date picker plugin. */
/* Written by Jacek Wysocki (jacek.wysocki@gmail.com). */
jQuery(function($){
    $.timepicker.regional['pl'] = {
	timeOnlyTitle: 'Wybierz godzinę',
	timeText: 'Czas',
	hourText: 'Godzina',
	minuteText: 'Minuta',
	secondText: 'Sekunda',
	millisecText: 'Milisekunda',
	timezoneText: 'Strefa czasowa',
	currentText: 'Teraz',
	closeText: 'Zrobione',
	timeFormat: 'hh:mm tt',
	amNames: ['AM', 'A'],
	pmNames: ['PM', 'P'],
	ampm: false
    };
    $.timepicker.setDefaults($.timepicker.regional['pl']);
});
