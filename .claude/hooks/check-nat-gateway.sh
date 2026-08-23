#!/usr/bin/env bash
# Warns if the app-pipeline NAT Gateway is left running (not free-tier, ~$0.05/hr).
# Fails silently on any error (expired session, aws CLI missing, etc.) so it never
# blocks a Claude Code session.

ids=$(aws ec2 describe-nat-gateways \
  --profile app-pipeline-terraform \
  --region eu-central-1 \
  --filter "Name=state,Values=available" \
  --query "NatGateways[?Tags[?Key=='Name' && starts_with(Value, 'app-pipeline')]].NatGatewayId" \
  --output text 2>/dev/null)

if [ -n "$ids" ]; then
  msg="⚠️  app-pipeline NAT Gateway is still running ($ids) — costs ~\$0.05/hr, NOT free-tier. Run 'terraform destroy' in infra/ if you're done for the session."
  jq -n --arg msg "$msg" '{systemMessage: $msg}'
fi

exit 0
