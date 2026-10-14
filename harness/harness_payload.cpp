// le "n temp" do stdin e imprime o payload montado pelo aluno
int main() {
  int n; double temp;
  if (scanf("%d %lf", &n, &temp) != 2) return 1;
  Serial.println(montaPayload(n, (float)temp));
  return 0;
}
