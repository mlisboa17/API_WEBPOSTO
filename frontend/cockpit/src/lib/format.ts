export function fmtBRL(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value ?? 0);
}

export function fmtBRLPreciso(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value ?? 0);
}

export function fmtLitros(value: number): string {
  return (
    new Intl.NumberFormat("pt-BR", {
      maximumFractionDigits: 0,
    }).format(value ?? 0) + " L"
  );
}

export function fmtLitrosPreciso(value: number): string {
  return (
    new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    }).format(value ?? 0) + " L"
  );
}
