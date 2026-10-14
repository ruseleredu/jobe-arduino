// Harness Tier A: testa UMA funcao do aluno lendo a entrada do stdin.
// Ajuste conforme a assinatura da funcao avaliada.
int main() {
  int n;
  if (scanf("%d", &n) != 1) return 1;
  printf("%d\n", ehPar((uint8_t)n) ? 1 : 0);
  return 0;
}
