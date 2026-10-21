/* Projeção pura do progresso do treino guiado. Não escreve DOM nem estado persistido.
 *
 * `next` é sempre a primeira série pendente na ordem da prescrição. O cursor
 * `focusIndex` (salto pela lista "Ver treino todo") só muda `current`: pular para
 * um exercício não marca nada como pulado, e quando o exercício focado fica sem
 * pendência o chamador limpa o cursor e o guia volta para a primeira pendente.
 * Concluído = todas as obrigatórias registradas, ao menos uma série por
 * exercício livre e ao menos uma série feita no treino.
 */
(function () {
  'use strict';

  function key(movementIndex, setNumber) {
    return movementIndex + ':' + setNumber;
  }

  function movementStatus(done, required, requiredDone, skipped, pending) {
    if (done > 0 && requiredDone === required) return 'done';
    if (!pending && !done) return 'skipped';
    if (!pending) return 'incomplete';
    if (done || skipped) return 'started';
    return 'pending';
  }

  function project(movements, recorded, skipped, pendingCount, lastSkipped, lastFreeformIndex, options) {
    var total = 0;
    var next = null;
    var requiredMissing = false;
    var missing = 0;
    var missingRequiredSets = 0;
    var missingFreeformMovements = 0;
    var focusIndex = options && options.focusIndex != null ? options.focusIndex : null;

    var overview = movements.map(function (movement, movementIndex) {
      var done = 0;
      var required = 0;
      var requiredDone = 0;
      var skippedCount = 0;
      var pending = [];
      movement.series.forEach(function (series, index) {
        var setNumber = index + 1;
        var setKey = key(movementIndex, setNumber);
        var isRecorded = recorded.has(setKey);
        total += 1;
        if (series.required) {
          required += 1;
          if (isRecorded) requiredDone += 1;
          else { requiredMissing = true; missing += 1; missingRequiredSets += 1; }
        }
        if (isRecorded) done += 1;
        else if (skipped.has(setKey)) skippedCount += 1;
        else pending.push({ movement: movement, movementIndex: movementIndex, setNumber: setNumber, series: series });
      });
      if (movement.freeform && done === 0 && required === 0) {
        requiredMissing = true;
        missing += 1;
        missingFreeformMovements += 1;
      }
      if (!next && pending.length) next = pending[0];
      return {
        index: movementIndex,
        status: movementStatus(done, required, requiredDone, skippedCount, pending.length),
        done: done, total: movement.series.length, skipped: skippedCount,
        firstPending: pending[0] || null, pending: pending,
      };
    });

    var current = next;
    if (focusIndex !== null && overview[focusIndex] && overview[focusIndex].firstPending) {
      current = overview[focusIndex].firstPending;
    }
    var upNext = null;
    if (current) {
      var sameMovement = overview[current.movementIndex].pending;
      upNext = sameMovement[sameMovement.indexOf(current) + 1] || null;
      if (!upNext) {
        overview.some(function (item) {
          if (item.index === current.movementIndex || !item.firstPending) return false;
          upNext = item.firstPending;
          return true;
        });
      }
    }

    return {
      next: next,
      current: current,
      upNext: upNext,
      overview: overview,
      total: total,
      missing: missing,
      missingRequiredSets: missingRequiredSets,
      missingFreeformMovements: missingFreeformMovements,
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
