import json, time

class Evaluator:
    def exact_match(self, gen, exp):
        norm = lambda s: ' '.join(s.upper().split())
        return norm(gen) == norm(exp)

    def run(self, dataset_path, intent_detector, sql_generator):
        with open(dataset_path) as f: ds = json.load(f)
        ok = 0; latencies = []; errors = 0

        for q in ds:
            t0 = time.time()
            try:
                intent = intent_detector.detect(q['question'])
                sql_r  = sql_generator.generate(intent, 'eval_user')
                em = self.exact_match(sql_r['sql'], q.get('expected_sql',''))
                if em: ok += 1
                latencies.append(int((time.time()-t0)*1000))
                status = "✓" if em else "✗"
                print(f"{status} {q['id']}: intent={intent.get('intent')} table={intent.get('table')}")
            except Exception as e:
                errors += 1; print(f"❌ {q['id']}: {e}")

        total = len(ds)
        print(f"\n{'='*40}")
        print(f"Exact Match : {ok}/{total} = {round(ok/total*100,1)}%")
        print(f"Latence moy : {round(sum(latencies)/len(latencies))}ms")
        print(f"Erreurs     : {errors}")