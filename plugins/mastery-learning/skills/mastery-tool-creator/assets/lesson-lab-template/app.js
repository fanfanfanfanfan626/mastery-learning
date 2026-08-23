const prediction = document.querySelector("#prediction");
const lockPrediction = document.querySelector("#lock-prediction");
const experiment = document.querySelector("#experiment");
const control = document.querySelector("#control-value");
const controlOutput = document.querySelector("#control-output");
const meter = document.querySelector("#meter-fill");
const summary = document.querySelector("#state-summary");
const tableInput = document.querySelector("#table-input");
const tableOutput = document.querySelector("#table-output");
const explanation = document.querySelector("#explanation");
const explanationFeedback = document.querySelector("#explanation-feedback");

function renderState() {
  const input = Number(control.value);
  const output = input * 2;
  controlOutput.textContent = String(input);
  tableInput.textContent = String(input);
  tableOutput.textContent = String(output);
  meter.style.width = `${Math.min(100, output * 10)}%`;
  summary.textContent = `Input ${input} produces output ${output}.`;
}

lockPrediction.addEventListener("click", () => {
  if (!prediction.value.trim()) {
    prediction.focus();
    prediction.setAttribute("aria-invalid", "true");
    return;
  }
  prediction.removeAttribute("aria-invalid");
  experiment.hidden = false;
  renderState();
  control.focus();
});

control.addEventListener("input", renderState);

document.querySelector("#check-explanation").addEventListener("click", () => {
  const response = explanation.value.trim();
  if (response.length < 24) {
    explanationFeedback.textContent = "Name the changed input, the fixed rule, and the resulting output.";
    explanation.focus();
    return;
  }
  explanationFeedback.textContent = "Your explanation is long enough to inspect. Compare it with the three-part hint, then submit it to the tutor for feedback.";
});
