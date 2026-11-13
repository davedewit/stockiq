#!/bin/bash
# Admin #15 (payments): the payment handler believes a Stripe event only when Stripe confirms it, cancels only for a proven asker, ignores the end
# of a subscription that is not the member's current one; the dashboard function no longer hands out subscription ids. Built by patch.py.
# Then the page that sends the proof: pending-payments-web (deploy it right after, with its own deploy.sh).
FUNCS="stockiq-payment-handler:lambda:lambda_function.py:783BzSSg2Vt+2D+ot02UdIFyQ8d90DW3vx8qHVMW6UM=:ecee1b4ccaea9b6b6b278fdf6a658746a2609d40b28f9bfdd74c9745d0402124:0ffe349a78fa8c4e93e295464cd9be649f546fb1a4e7a2c823ec8568906dbfe7:before_payments_20261112 stockiq-dashboard:dashboard:lambda_function.py:hwJHpJvbdiCl/cgoG+BmvJpZPQW3VshL201o6EfH9jU=:8cc8669e4bfdad95d4b6ac2971dace31869ca428114e05e91ae4419d60225c8c:df87121e5830027712f7a4d79ac3adce949cea5d2a311456e8d5d9d3aaf77a7f:before_payments_20261112" \
  exec bash /Users/dave/VSCODE/stockiq/check-tools/lambda_deploy.sh "$(cd "$(dirname "$0")" && pwd)"
