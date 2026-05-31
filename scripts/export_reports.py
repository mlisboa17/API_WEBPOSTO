#!/usr/bin/env python3
"""
Exportador de relatórios WebPosto

Uso:
  python scripts/export_reports.py --report resumo_vendas --start 2026-04-01 --end 2026-04-30 --format json --out ./scripts/reports

O script busca o token em `WEBPOSTO_BEARER_TOKEN` (variável de ambiente) ou pergunta interativamente.
Salva saída como JSON; se `--format csv` e o payload for lista de objetos, converte para CSV simples.
"""

import argparse
import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path
from datetime import date, timedelta

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_BASE = os.environ.get('VITE_API_BASE') or os.environ.get('API_BASE') or 'http://localhost:8000'


def build_session(retries=3, backoff=0.3, status_forcelist=(429, 500, 502, 503, 504)):
    s = requests.Session()
    r = Retry(total=retries, backoff_factor=backoff, status_forcelist=status_forcelist, allowed_methods=None)
    s.mount('https://', HTTPAdapter(max_retries=r))
    s.mount('http://', HTTPAdapter(max_retries=r))
    return s


def fetch_report(session, base, report_path, params, token=None, timeout=20):
    url = base.rstrip('/') + report_path
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    resp = session.get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp


def save_json(obj, path: Path):
    with path.open('w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def to_csv_from_list(lst, path: Path):
    # simple flatten: collect all keys
    if not isinstance(lst, list):
        raise ValueError('payload is not a list')
    keys = set()
    for item in lst:
        if isinstance(item, dict):
            keys.update(item.keys())
    keys = sorted(keys)
    import csv

    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        for item in lst:
            row = [item.get(k, '') if isinstance(item, dict) else '' for k in keys]
            writer.writerow(row)


def main():
    p = argparse.ArgumentParser(description='Exportador de relatórios WebPosto')
    p.add_argument('--report', '-r', required=True, help='Identificador do relatório (ex: /INTEGRACAO/RELATORIO/RESUMO_VENDAS) ou resumo_vendas')
    p.add_argument('--id', help='ID de recurso específico (ex: TIT_ABC123XYZ) - será anexado ao endpoint quando informado')
    p.add_argument('--centro', '--centro-custo', dest='centro', help='Filtrar por centro de custo')
    p.add_argument('--filial', help='Filtrar por filial (id ou código)')
    p.add_argument('--plano', '--plano-de-conta', dest='plano', help='Filtrar por plano de contas')
    p.add_argument('--start', help='Data inicio (YYYY-MM-DD)')
    p.add_argument('--end', help='Data fim (YYYY-MM-DD)')
    p.add_argument('--format', '-f', choices=['json', 'csv'], default='json')
    p.add_argument('--out', '-o', default='./scripts/reports', help='Pasta de saída')
    p.add_argument('--base', default=DEFAULT_BASE, help='Base URL da API')
    p.add_argument('--token', help='Bearer token (opcional). Se ausente, usa WEBPOSTO_BEARER_TOKEN')
    args = p.parse_args()

    report_map = {
        'resumo_vendas': '/INTEGRACAO/RELATORIO/RESUMO_VENDAS',
        'venda_combustivel': '/INTEGRACAO/RELATORIO/VENDA_COMBUSTIVEL',
        'estoque': '/INTEGRACAO/RELATORIO/ESTOQUE',
        'titulo_pagar': '/INTEGRACAO/TITULO_PAGAR',
        'titulo_receber': '/INTEGRACAO/TITULO_RECEBER',
        'titulo': '/api/v1/financeiro',
        'despesas_caixa': '/INTEGRACAO/CAIXA',
        # você pode adicionar mais aliases aqui
    }

    report_path = report_map.get(args.report.lower(), args.report if args.report.startswith('/') else f'/{args.report}')

    # if an ID is provided, append it to the path (or replace {id} if template used)
    if args.id:
        if '{id}' in report_path:
            report_path = report_path.replace('{id}', args.id)
        else:
            report_path = report_path.rstrip('/') + '/' + args.id

    # map external WebPosto paths to local API equivalents when testing locally
    if 'localhost' in args.base:
        # prefer internal CRUD routes
        if report_path.upper().startswith('/INTEGRACAO/CAIXA'):
            report_path = '/api/v1/caixa'
        if report_path.upper().startswith('/INTEGRACAO/ABASTECIMENTO'):
            report_path = '/api/v1/abastecimentos'

    token = args.token or os.environ.get('WEBPOSTO_BEARER_TOKEN')
    if not token:
        try:
            import getpass
            token = getpass.getpass('WEBPOSTO token (input oculto): ')
        except Exception:
            token = input('WEBPOSTO token: ')

    params = {}
    if args.start:
        params['data_inicio'] = args.start
    if args.end:
        params['data_fim'] = args.end

    # additional filters passed as query params
    if args.centro:
        params['centro_custo'] = args.centro
    if args.filial:
        params['filial'] = args.filial
    if args.plano:
        params['plano_de_conta'] = args.plano

    # default start/end to yesterday if user requested caixa despesas or not provided
    if (args.report.lower() in ('despesas_caixa', 'titulo_pagar', 'titulo_receber') ):
        if not args.start or not args.end:
            yesterday = date.today() - timedelta(days=1)
            y = yesterday.strftime('%Y-%m-%d')
            if not args.start:
                params['data_inicio'] = y
            if not args.end:
                params['data_fim'] = y

    session = build_session()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    safe_name = report_path.strip('/').replace('/', '_')
    base_fname = f"{safe_name}_{args.start or 'start'}_{args.end or 'end'}_{timestamp}"

    try:
        resp = fetch_report(session, args.base, report_path, params, token=token)
        try:
            payload = resp.json()
        except ValueError:
            # non-json response
            text = resp.text
            out_file = out_dir / (base_fname + '.txt')
            out_file.write_text(text, encoding='utf-8')
            print(f'Salvo texto em: {out_file}')
            return

        out_file = out_dir / (base_fname + '.json')
        save_json(payload, out_file)
        print(f'Salvo JSON em: {out_file}')

        if args.format == 'csv':
            # Special handling for despesas_caixa: extract movimentos and filter saídas
            def write_csv_from_list(lst, target_path):
                # if report is despesas_caixa, try to filter only outflows
                filtered = lst
                try:
                    if args.report.lower() == 'despesas_caixa':
                        def is_out(item):
                            if not isinstance(item, dict):
                                return False
                            t = str(item.get('tipo', '')).lower()
                            cat = str(item.get('categoria', '')).lower()
                            # common indicators
                            return ('saida' in t) or ('saida' in cat) or ('desp' in cat)
                        filtered = [i for i in lst if is_out(i)]
                except Exception:
                    filtered = lst

                if not filtered:
                    print('Nenhum registro encontrado para conversão CSV (após filtro).')
                    return

                # choose columns
                cols = ['id', 'data', 'descricao', 'valor', 'tipo', 'categoria', 'fornecedor', 'vencimento', 'centro_custo', 'filial', 'plano_de_conta']
                import csv
                with target_path.open('w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(cols)
                    for it in filtered:
                        if not isinstance(it, dict):
                            continue
                        row = [it.get(c, '') for c in cols]
                        writer.writerow(row)

            if isinstance(payload, dict):
                # try to find the list of movimentos or first list
                lst = None
                if 'movimentos' in payload and isinstance(payload['movimentos'], list):
                    lst = payload['movimentos']
                else:
                    for v in payload.values():
                        if isinstance(v, list):
                            lst = v
                            break

                if lst is None:
                    print('Nenhuma lista encontrada no JSON para converter em CSV.')
                else:
                    csv_file = out_dir / (base_fname + '.csv')
                    write_csv_from_list(lst, csv_file)
                    print(f'Salvo CSV em: {csv_file}')
            elif isinstance(payload, list):
                csv_file = out_dir / (base_fname + '.csv')
                write_csv_from_list(payload, csv_file)
                print(f'Salvo CSV em: {csv_file}')
            else:
                print('Resposta não é lista/dicionário para conversão CSV.')

    except requests.HTTPError as e:
        print('Erro HTTP:', e, file=sys.stderr)
        if e.response is not None:
            try:
                print('Corpo:', e.response.json(), file=sys.stderr)
            except Exception:
                print('Corpo texto:', e.response.text, file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print('Erro:', e, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
