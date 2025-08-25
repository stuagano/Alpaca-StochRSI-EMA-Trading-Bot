#!/usr/bin/env node

/**
 * Test MCP Workflow for Claude Flow Integration
 * This script validates that MCP tools are properly configured and functional
 */

const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);

// Color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m'
};

async function runCommand(command, description) {
  console.log(`${colors.blue}Running: ${description}${colors.reset}`);
  try {
    const { stdout, stderr } = await execPromise(command);
    console.log(`${colors.green}✓ Success${colors.reset}`);
    if (stdout) console.log(stdout);
    return { success: true, output: stdout };
  } catch (error) {
    console.log(`${colors.red}✗ Failed${colors.reset}`);
    console.error(error.message);
    return { success: false, error: error.message };
  }
}

async function testMCPWorkflow() {
  console.log(`${colors.yellow}=== MCP Claude Flow Test Workflow ===${colors.reset}\n`);

  const tests = [
    {
      command: 'claude-flow --version',
      description: 'Check Claude Flow version'
    },
    {
      command: 'claude-flow status',
      description: 'Check system status'
    },
    {
      command: 'claude-flow memory list',
      description: 'List memory namespaces'
    },
    {
      command: 'claude-flow memory store test-key "test-value"',
      description: 'Test memory storage'
    },
    {
      command: 'claude-flow memory retrieve test-key',
      description: 'Test memory retrieval'
    },
    {
      command: 'claude-flow hooks pre-task --description "test task"',
      description: 'Test pre-task hook'
    },
    {
      command: 'claude-flow hooks post-task --task-id "test-123"',
      description: 'Test post-task hook'
    },
    {
      command: 'claude-flow agent list',
      description: 'List available agents'
    },
    {
      command: 'claude-flow sparc --help',
      description: 'Check SPARC modes'
    }
  ];

  let successCount = 0;
  let failureCount = 0;

  for (const test of tests) {
    const result = await runCommand(test.command, test.description);
    if (result.success) {
      successCount++;
    } else {
      failureCount++;
    }
    console.log('---\n');
  }

  console.log(`${colors.yellow}=== Test Summary ===${colors.reset}`);
  console.log(`${colors.green}Passed: ${successCount}${colors.reset}`);
  console.log(`${colors.red}Failed: ${failureCount}${colors.reset}`);
  
  if (failureCount === 0) {
    console.log(`\n${colors.green}All MCP tests passed successfully!${colors.reset}`);
  } else {
    console.log(`\n${colors.red}Some tests failed. Please check the configuration.${colors.reset}`);
  }
}

// Run the test workflow
testMCPWorkflow().catch(console.error);