/* Projeção pura do progresso do treino guiado. Não escreve DOM nem estado persistido. */
(function () {
  'use strict';

  function key(movementIndex, setNumber) {
    return movementIndex + ':' + setNumber;
  }

  function project(movements, recorded, skipped, pendingCount, lastSkipped, lastFreeformIndex) {
    var total = 0;
    var next = null;
    var requiredMissing = false;

    movements.forEach(function (movement, movementIndex) {
      movement.series.forEach(function (series, index) {
        var setNumber = index + 1;
        var setKey = key(movementIndex, setNumber);
        total += 1;
        if (series.required && !recorded.has(setKey)) requiredMissing = true;
        if (!next && !recorded.has(setKey) && !skipped.has(setKey)) {
          next = { movement: movement, movementIndex: movementIndex, setNumber: setNumber, series: series };
        }
      });
    });

    return {
      next: next,
      total: total,
      recordedCount: recorded.size,
      pendingCount: pendingCount,
      requiredMissing: requiredMissing,
      canFinish: !requiredMissing && recorded.size > 0,
      canUndoSkip: !!lastSkipped,
      canCorrect: recorded.size > 0,
      canAddExtra: lastFreeformIndex !== null && !!movements[lastFreeformIndex]
        && movements[lastFreeformIndex].series.length < 30,
    };
  }

  window.CurvaGuidedState = { key: key, project: project };
})();
