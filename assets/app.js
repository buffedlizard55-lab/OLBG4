// Minimal table filter for the fixture tables. No dependencies, no tracking.
document.querySelectorAll('input[data-filter]').forEach(function (input) {
  var wrap = input.closest('.filters') ? input.closest('.filters').nextElementSibling : null;
  if (!wrap) return;
  var table = wrap.querySelector('table');
  if (!table) return;
  input.addEventListener('input', function () {
    var q = input.value.trim().toLowerCase();
    var rows = table.tBodies[0].rows, shown = 0;
    for (var i = 0; i < rows.length; i++) {
      var match = q === '' || rows[i].textContent.toLowerCase().indexOf(q) !== -1;
      rows[i].style.display = match ? '' : 'none';
      if (match) shown++;
    }
    var note = wrap.parentElement.querySelector('.filternote');
    if (!note) {
      note = document.createElement('p');
      note.className = 'filternote small';
      wrap.parentElement.insertBefore(note, wrap);
    }
    note.textContent = shown + ' of ' + rows.length + ' rows shown';
  });
});
