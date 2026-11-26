package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestRun(t *testing.T) {
	tests := []struct {
		name       string
		args       []string
		wantCode   int
		wantStdout string // substring; "" means stdout must be empty
		wantStderr string
	}{
		{name: "version", args: []string{"version"}, wantCode: 0, wantStdout: "gumption dev"},
		{name: "version flag", args: []string{"--version"}, wantCode: 0, wantStdout: "gumption dev"},
		{name: "help", args: []string{"help"}, wantCode: 0, wantStdout: "Usage:"},
		{name: "no args", args: nil, wantCode: 2, wantStderr: "Usage:"},
		{name: "unknown", args: []string{"bogus"}, wantCode: 2, wantStderr: `unknown command "bogus"`},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := run(tt.args, &stdout, &stderr)
			if code != tt.wantCode {
				t.Errorf("exit code = %d, want %d", code, tt.wantCode)
			}
			if tt.wantStdout == "" && stdout.Len() != 0 {
				t.Errorf("stdout = %q, want empty", stdout.String())
			}
			if !strings.Contains(stdout.String(), tt.wantStdout) {
				t.Errorf("stdout = %q, want it to contain %q", stdout.String(), tt.wantStdout)
			}
			if !strings.Contains(stderr.String(), tt.wantStderr) {
				t.Errorf("stderr = %q, want it to contain %q", stderr.String(), tt.wantStderr)
			}
		})
	}
}

func TestVersionStringStamped(t *testing.T) {
	old := version
	t.Cleanup(func() { version = old })
	version = "v1.2.3"
	if got := versionString(); !strings.HasPrefix(got, "gumption v1.2.3") {
		t.Errorf("versionString() = %q, want prefix %q", got, "gumption v1.2.3")
	}
}
